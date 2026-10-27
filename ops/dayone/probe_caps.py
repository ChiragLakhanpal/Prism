# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = []
# ///
"""Day-one test 8 and the Azure caps: each deployment's limit, the budget, and the subscription's offer.

Run it from the main checkout after the wizard:

    uv run --script ops/dayone/probe_caps.py --env-file .env

It uses the Azure command line the wizard signed in. It prints a tokens-per-minute limit for
each of the four deployments that config/models.toml names, checks that a budget sends alerts, and
reads whether the subscription is on pay-as-you-go. It writes test 8, the caps block and, once the
subscription shows pay-as-you-go, the pay-as-you-go block in docs/day-one-results.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dayone  # noqa: E402
from dayone import Outcome, ProbeError, SetupError  # noqa: E402

STANDARD_SKUS = {"Standard", "GlobalStandard", "DataZoneStandard"}
SKU_NAMES = {"GlobalStandard": "Global Standard", "GlobalBatch": "Global Batch", "Standard": "Standard",
             "DataZoneStandard": "Data Zone Standard", "DataZoneBatch": "Data Zone Batch"}
GRAINS = {"Monthly": "a month", "Quarterly": "a quarter", "Annually": "a year"}


def token_limit(deployment: dict) -> int | None:
    """Tokens per minute: the token rate limit Azure reports, or a standard deployment's capacity."""
    for limit in deployment.get("properties", {}).get("rateLimits") or []:
        if limit.get("key") == "token" and limit.get("renewalPeriod") == 60:
            return int(limit["count"])
    sku = deployment.get("sku") or {}
    if sku.get("name") in STANDARD_SKUS and sku.get("capacity"):
        return int(sku["capacity"]) * 1000
    return None


def deployment_line(name: str, deployment: dict, cap: dict) -> tuple[str, bool]:
    """One printed line for a deployment, and whether its cap holds."""
    sku = deployment.get("sku") or {}
    kind = SKU_NAMES.get(sku.get("name"), sku.get("name") or "an unknown type")
    if "enqueued_tokens" in cap:
        return batch_line(name, kind, sku.get("capacity"), cap)
    tpm = token_limit(deployment)
    if tpm is None:
        return f"{name}: no tokens-per-minute limit, as {kind}.", False
    if tpm > cap["tokens_per_minute"]:
        return (f"{name}: {tpm:,} tokens per minute, as {kind}. That is above the cap of "
                f"{cap['tokens_per_minute']:,} in dayone.toml."), False
    return f"{name}: {tpm:,} tokens per minute, as {kind}.", True


def batch_line(name: str, kind: str, capacity, cap: dict) -> tuple[str, bool]:
    """A batch deployment's line. Azure reports its capacity in the unit dayone.toml names."""
    if not capacity:
        return f"{name}: {kind}, with no enqueued-token limit that Azure reports.", False
    tokens = int(capacity) * cap.get("capacity_unit", 1)
    line = (f"{name}: {tokens:,} enqueued tokens, as {kind}. A {kind} deployment has no tokens-per-minute "
            "limit, so Azure caps the tokens it holds in the queue instead.")
    if tokens > cap["enqueued_tokens"]:
        return f"{line} That is above the cap of {cap['enqueued_tokens']:,} in dayone.toml.", False
    return line, True


def budget_line(budgets: list[dict], config: dict) -> tuple[str, bool]:
    if not budgets:
        return "The subscription has no budget, so nobody hears about spend.", False
    wanted = config["names"]["budget"]
    budget = next((b for b in budgets if b.get("name") == wanted), budgets[0])
    props = budget.get("properties") or {}
    amount = f"US${float(props.get('amount', 0)):,.0f} {GRAINS.get(props.get('timeGrain'), 'per period')}"
    alerts = [n for n in (props.get("notifications") or {}).values()
              if n.get("enabled") and (n.get("contactEmails") or n.get("contactGroups") or n.get("contactRoles"))]
    if not alerts:
        return f"{budget.get('name')}: {amount}, with no alerts, so nobody hears about spend.", False
    actual = sorted(int(n["threshold"]) for n in alerts if n.get("thresholdType", "Actual") == "Actual")
    forecast = sorted(int(n["threshold"]) for n in alerts if n.get("thresholdType") == "Forecasted")
    parts = []
    if actual:
        parts.append(f"actual cost at {', '.join(map(str, actual))} percent")
    if forecast:
        parts.append(f"forecast cost at {', '.join(map(str, forecast))} percent")
    people = {address for n in alerts for address in n.get("contactEmails") or []}
    alerts_text = dayone.count_words(len(alerts), "alert")
    people_text = dayone.count_words(len(people), "email address", "email addresses")
    return f"{budget.get('name')}: {amount}, with {alerts_text} ({'; '.join(parts)}), sent to {people_text}.", True


def offer_line(subscription: dict) -> tuple[str, bool]:
    policies = subscription.get("subscriptionPolicies") or {}
    quota = policies.get("quotaId", "unknown")
    if quota.startswith("PayAsYouGo"):
        offer = "pay-as-you-go"
    elif quota.startswith("FreeTrial"):
        offer = "the free trial"
    else:
        offer = f"the offer {quota}"
    name = subscription.get("displayName", "The subscription")
    return (f"{name} is on {offer} (quota ID {quota}, spending limit {policies.get('spendingLimit', 'unknown')}).",
            offer == "pay-as-you-go")


def check(azure, config: dict, models: dict):
    """Returns test 8's Outcome, the caps block's fields and whether the subscription is pay-as-you-go.

    models is the model file's roles (dayone.models()), which name the deployments. dayone.toml
    holds only each role's cap.
    """
    today = dayone.dt.date.today()
    try:
        found = {d.get("name"): d for d in azure.deployments()}
    except SetupError as error:  # az could not read anything, so the wizard's record of test 8 stays
        return dayone.not_run(error), None, False
    except ProbeError as error:
        outcome = Outcome("failed", "I could not read the deployments.", [str(error)])
        return outcome, None, False
    lines, missing, capped = [], [], True
    for role, cap in config["caps"]["deployments"].items():
        name = models[role].deployment
        deployment = found.get(name)
        if deployment is None:
            lines.append(f"{name}: not found in {config['names']['foundry_resource']}.")
            missing.append(name)
            capped = False
            continue
        state = (deployment.get("properties") or {}).get("provisioningState", "unknown")
        line, holds = deployment_line(name, deployment, cap)
        if state != "Succeeded":
            line += f" Its state is {state}."
            missing.append(name)
        lines.append(line)
        capped = capped and holds
    try:
        budget, budget_ok = budget_line(azure.budgets(), config)
    except ProbeError as error:
        budget, budget_ok = f"I could not read the budgets. {error}", False
    try:
        offer, payg = offer_line(azure.subscription())
    except ProbeError as error:
        offer, payg = f"I could not read the subscription. {error}", False

    if missing:
        outcome = Outcome("failed", f"These deployments are missing or not ready: {', '.join(missing)}.", lines)
    else:
        outcome = Outcome("passed", "Every deployment with a cap in dayone.toml exists and finished deploying.",
                          lines)
    caps = [
        ("Status", dayone.CAPS_STATUSES[0] if capped and budget_ok else dayone.CAPS_STATUSES[1]),
        ("Deployments", lines),
        ("Budget", budget),
        ("Subscription offer", offer),
        ("Last checked", dayone.long_date(today)),
    ]
    return outcome, caps, payg


class CannedAzure:
    """What a capped subscription on the free trial looks like, for --dry-run."""

    def __init__(self, config: dict, models: dict):
        self.config, self.models = config, models

    def deployments(self):
        rows = []
        for role, cap in self.config["caps"]["deployments"].items():
            if "enqueued_tokens" in cap:
                capacity = cap["enqueued_tokens"] // cap.get("capacity_unit", 1)
            else:
                capacity = cap["tokens_per_minute"] // 1000  # a standard deployment counts thousands per minute
            rows.append({"name": self.models[role].deployment, "sku": {"name": cap["sku"], "capacity": capacity},
                         "properties": {"provisioningState": "Succeeded"}})
        return rows

    def budgets(self):
        alert = {"enabled": True, "threshold": 80, "thresholdType": "Actual", "contactEmails": ["owner"]}
        return [{"name": self.config["names"]["budget"],
                 "properties": {"amount": self.config["caps"]["monthly_budget_usd"], "timeGrain": "Monthly",
                                "notifications": {"actual_80": alert}}}]

    def subscription(self):
        return {"displayName": "Dry-run subscription",
                "subscriptionPolicies": {"quotaId": "FreeTrial_2014-09-01", "spendingLimit": "On"}}


def main(argv: list[str] | None = None, service=None) -> int:
    args = dayone.probe_args(argv, __doc__)
    config = dayone.load_config()
    try:
        dayone.probe_env(args, [])  # the az sign-in comes from the wizard, so the env file must exist
        models = dayone.models()
        if service is None:
            if args.dry_run:
                service = CannedAzure(config, models)
            else:
                from live import LiveAzure
                service = LiveAzure(config)
        outcome, caps, payg = check(service, config, models)
    except (dayone.DayOneError, ProbeError) as error:
        print(error, file=sys.stderr)
        return 2

    status = dict(caps or [("Status", "not checked")])
    print("Azure caps")
    for name, value in caps or []:
        if isinstance(value, list):
            print(f"  {name}:")
            for line in value:
                print(f"    - {line}")
        else:
            print(f"  {name}: {value}")
    code = dayone.report_test(8, outcome, args, config)
    if not args.dry_run and caps:
        results = args.results or dayone.default_results_path(config)
        dayone.record_block(results, "caps", caps, config)
        if payg:
            who = dayone.read_results(results).get("payg", {}).get("Who") or config["payg"]["who"]
            dayone.record_payg(results, "shows pay-as-you-go", who, None, config=config)
            print("The subscription shows pay-as-you-go, so I marked that step done.")
    return code if status.get("Status") == dayone.CAPS_STATUSES[0] else 1


if __name__ == "__main__":
    sys.exit(main())
