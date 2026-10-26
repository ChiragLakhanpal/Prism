# Moving Strata to a paid Azure Databricks workspace

Written on October 26, 2026, for the person at the keyboard. Every claim about Azure or Databricks ends with the page it came from. Every command is one the repo holds, copied as the repo prints it, except the three copy commands for the env file, which this guide adds. No secret value appears here, only key names. Where I could not confirm a fact, the sentence says so.

## 1. What you get, how long it takes, what you need

At the end you have a Premium Azure Databricks workspace in the resource group WorldBank-demo, beside Foundry, with Strata's catalog, jobs, dashboards, Genie space, AI Search endpoint and App deployed on it from code, and the day-one results recorded on it. The Free Edition workspace stays as it is. Section 9 switches back with two commands.

Time. Your own clicks and typing take about 25 minutes: the portal form, the checks after it, and the wizard. The deploy chain is mostly waiting, about three hours. Most of that is the nightly job's first run, which stops after 150 minutes at the latest.

Before you start, you need these things.

1. An Azure subscription with rights to create resources in WorldBank-demo. Databricks asks for Contributor or Owner at the subscription level, or a custom role with the permissions it lists. The subscription must not be a Free Trial subscription, and its spending limit must be removed. Yours showed pay-as-you-go on October 24, 2026 (docs/day-one-results.md, the pay-as-you-go block). Source: https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/
2. The Databricks account admin role, only if a Unity Catalog metastore has to be made in the region (section 8, problem 1). The first person to sign in to the account console must be a Microsoft Entra ID Global Administrator at that moment. Source: https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/create-metastore
3. The repo at the main checkout, on the branch build/strata, with the Databricks CLI 0.287.0 or later, az, uv, npm and web/node_modules present. The bundle needs that CLI version (bundle/README.md, "Deploy"), and the App deploy needs npm (ops/app/deploy_app.py).
4. A copy of the current env file. Run this in your own terminal, from the main checkout, before anything else:

   ```
   cp .env .env.free-edition
   ```

   git ignores every .env.* name except .env.example (.gitignore lines 2 to 4), so the copy stays out of git. The guard in agent sessions blocks any command that names an env file, so this copy and the switch back in section 9 are yours to run, not a session's.
5. The region of the Foundry resource wb-strata. Open wb-strata in the portal and read "Location" on its Overview page. The repo does not record the region, and Application Insights was made in that region (ops/wizard/strata-setup.sh, stage 9), so the workspace should sit there too when the region offers everything Strata needs. Section 2 says how to check.

## 2. Create the workspace, tab by tab

In the Azure portal, click Create a resource, then Analytics, then Azure Databricks. Source: https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/create-workspace

### Basics tab

1. "Subscription": pick the subscription that holds WorldBank-demo. Databricks bills through the Azure subscription, and the budget in section 7 lives there. Source: https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-trial-vs-free-edition
2. "Resource group": pick WorldBank-demo. Foundry, Application Insights and the Entra app registration strata-app are there, and the daily cost pull asks Azure for that group's charges only (config/budget.toml, [pull] resource_group). The workspace's charges show on the Governance page only when the workspace is in that group.
3. "Workspace name": a short name with no spaces, and not strata. A new workspace gets a catalog of its own, named after the workspace, and the bundle creates a catalog named strata, which must not exist already (bundle/README.md, "Some things to know before the first deploy"). A name such as strata-azure works. Source: https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/setup-uc
4. "Location", which the portal may call Region: pick the region you read from wb-strata, if it is one of these 14: australiaeast, brazilsouth, canadacentral, centralindia, centralus, eastus, eastus2, northeurope, southcentralus, southeastasia, uksouth, westeurope, westus, westus2. Those are the regions with a tick for serverless compute, serverless workspaces, default storage, Databricks Apps and Lakebase on the one region table, and every one of them has AI Search too. If wb-strata's region is not on the list, pick the nearest one that is. A resource group may hold resources in different regions, though Microsoft recommends one region. Sources: https://learn.microsoft.com/en-us/azure/databricks/resources/feature-region-support and https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/overview
5. "Pricing Tier": Premium. Since April 1, 2026 every new workspace must be Premium, and everything Strata uses is Premium only: Unity Catalog, SQL warehouses, serverless compute, Databricks Apps, Lakebase and Genie Code. The page also lists "Trial (Premium - 14-Days Free DBUs)", which gives free Premium DBUs for 14 days. The page does not say what happens on day 15, so this guide picks Premium. Sources: https://learn.microsoft.com/en-us/azure/databricks/admin/account-settings/standard-tier, https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/ and https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-trial
6. "Workspace type": Serverless. Strata runs only serverless compute. Every job task carries environment_key default (bundle/nightly.yml, bundle/costs.yml, bundle/lessons.yml, bundle/retrieval.yml), the warehouse is serverless, and the App, Lakebase, Genie and AI Search are the uses Databricks names as reasons to pick a serverless workspace. A serverless workspace comes with serverless compute and default storage, and has no managed resource group and no classic compute, so there is no managed VNet and no NAT gateway to pay for. Default storage is also what the Free Edition metastore used, so the catalog path the repo already worked through applies (section 8, problem 5). The portal marks this type Public Preview. Two things I could not confirm from the pages I read: whether the Networking tab still appears for this type, and whether every feature behaves on Azure as it did on the AWS Free Edition. If you would rather stay on the generally available path, pick Hybrid and use the Networking tab below. Databricks plans to deprecate that creation path with a Databricks-managed VNet on a date it has not announced. Sources: https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/, https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/serverless-workspaces, https://learn.microsoft.com/en-us/cli/azure/databricks/workspace?view=azure-cli-latest, https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/secure-cluster-connectivity and https://learn.microsoft.com/en-us/azure/databricks/release-notes/whats-coming
7. "Managed Resource Group name", shown for Hybrid only: leave the default. Nothing in the repo names this group, and the daily cost pull reads WorldBank-demo only (config/budget.toml, [pull] resource_group), so its name does not matter to Strata. The default is databricks-rg-<workspace name>-<unique string>. The Serverless type has no managed resource group, which is why the portal shows the field for Hybrid only. Sources: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/secure-cluster-connectivity, https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/vnet-inject and https://learn.microsoft.com/en-us/cli/azure/databricks/workspace

### Networking tab

This tab belongs to the Hybrid type. If it appears, pick these.

1. "Deploy Azure Databricks workspace with Secure Cluster Connectivity (No Public IP)": Yes, the default. It removes public IP addresses from classic compute VMs and open ports from the VNet. It says nothing about who can open the workspace in a browser, and Databricks plans to make it mandatory. Source: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/secure-cluster-connectivity
2. "Deploy Azure Databricks workspace in your own Virtual Network (VNet)": No. Your own VNet is for private endpoints, on-premises routes, traffic inspection and custom DNS. Strata needs none of these. It reaches only the World Bank's public hosts, Azure OpenAI, Foundry and Application Insights. Your own VNet would also need a VNet in the same region, two subnets of at least /26 that nothing else shares, Network contributor on the VNet and, since March 31, 2026, a NAT gateway for outbound traffic, and the subnet ranges cannot change after deployment. With No, Databricks makes and manages the VNet. Source: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/vnet-inject
3. "Allow Public Network Access": Enabled, the default. Your Mac, the second session on it and the panel's browsers all come from the public internet, as they did on the Free Edition workspace (docs/day-one-results.md, test 1's evidence). With Disabled, all user traffic must come from a VNet joined through a private endpoint, which means a VPN, ExpressRoute or a jump box VM for every person. Sources: https://learn.microsoft.com/en-us/azure/databricks/security/network/front-end/front-end-private-connect and https://learn.microsoft.com/en-us/azure/databricks/security/network/concepts/privatelink-concepts
4. "Required NSG Rules": All Rules, the default. The other value, No Azure Databricks Rules, is for a classic compute plane Private Link connection only, and it removes the outbound rule classic compute uses to reach the control plane. Sources: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/private-link-standard and https://learn.microsoft.com/en-us/azure/databricks/security/network/concepts/privatelink-concepts
5. Private endpoints: do not create any. A front-end private endpoint needs VNet injection, a transit VNet, the private DNS zone privatelink.azuredatabricks.net and a second endpoint for browser sign-in, and you can test it only from a machine on that VNet, by VPN, ExpressRoute or a jump box. The docs themselves advise keeping public access on while testing. Sources: https://learn.microsoft.com/en-us/azure/databricks/security/network/front-end/front-end-private-connect and https://learn.microsoft.com/en-us/azure/databricks/security/network/concepts/privatelink-concepts
6. "Deploy Azure Databricks workspace with NAT Gateway": the docs show this option in the own-VNet flow and say to pick No there. With No for your own VNet, leave it as the portal shows it. Source: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/private-link-standard
7. If you later want to limit who can open the workspace from the internet, the docs' tool is an IP access list, set after creation with the CLI. A panel that opens Strata from changing home and office addresses would be locked out by one, so this guide sets none. Source: https://learn.microsoft.com/en-us/azure/databricks/security/network/front-end/ip-access-list-workspace

Serverless parts never use these settings. Serverless SQL warehouses have no public IP addresses, and VNet injection does not apply to them. Source: https://learn.microsoft.com/en-us/azure/databricks/admin/sql/serverless

### Encryption tab

1. Leave everything as it is. Microsoft manages the keys by default, for the managed disks and the storage account. Customer-managed keys need a key in Azure Key Vault, and the CLI can add or revert them later. Source: https://learn.microsoft.com/en-us/azure/databricks/security/keys/

### Security and compliance tab

1. "Enable compliance security profile": leave the box unticked. It needs the Enhanced Security and Compliance add-on on the account, it is meant as a permanent change, and with it on, the Partner-powered AI features setting that Genie needs is off by default. Source: https://learn.microsoft.com/en-us/azure/databricks/security/privacy/enhanced-security-compliance
2. "Enable enhanced security monitoring": leave the box unticked. It adds the add-on, and its monitoring agents run on classic compute only, which Strata has none of. Source: https://learn.microsoft.com/en-us/azure/databricks/security/privacy/enhanced-security-monitoring
3. "Enable automatic cluster update": leave the box unticked. It applies to compute in the classic compute plane and not to serverless compute, and Strata runs only serverless compute. Sources: https://learn.microsoft.com/en-us/azure/databricks/admin/clusters/automatic-cluster-update and https://learn.microsoft.com/en-us/azure/databricks/security/privacy/enhanced-security-compliance
4. The add-on's price: a search snippet of the Azure pricing page says 10 percent on top of the workspace's Databricks spend. I could not open that page, so check it in a browser if you ever turn these on.

### Tags tab

1. Optional. Leave it empty, or add one tag, such as project with the value strata. Tags on the workspace reach the cost analysis reports in the portal. Source: https://learn.microsoft.com/en-us/azure/databricks/admin/account-settings/usage-detail-tags

### Review and create

1. Open the Review and create tab, read the summary, and click Create.
2. Wait until the portal says the deployment is complete, then click Go to resource, then Launch Workspace. Your account is added as a workspace admin. A failed deployment still creates the workspace, and deleting a workspace also deletes its managed resource group. Source: https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/create-workspace

## 3. After it deploys: check the workspace

Open the workspace with Launch Workspace on the resource's Overview page. Its address has the form https://adb-1234567890123456.7.azuredatabricks.net. Copy it; the wizard asks for it. Source: https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/pat

1. Unity Catalog. Where: the account console at https://accounts.azuredatabricks.net, then Workspaces, then the Metastore column for your workspace. A metastore name there means Unity Catalog is on. Workspaces created after November 9, 2023 get it on their own, with a catalog named after the workspace, which you see under Catalog in the workspace's left menu. If the account console refuses you because you are not a Global Administrator, the docs give a one-line check for the SQL editor, SELECT CURRENT_METASTORE(); and a name in the answer means the same. If there is no metastore, section 8, problem 1 has the steps. Write down the name of the workspace's own catalog; section 4 needs it. Sources: https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/get-started and https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/setup-uc
2. Serverless compute. Nothing to turn on. A workspace with Unity Catalog in a supported region has it, and serverless SQL warehouses are on by default. Where: Compute in the left menu, then SQL Warehouses. If no warehouse is listed, click Create SQL warehouse, keep the serverless type, set the cluster size to 2X-Small and the Auto stop to 10 minutes or less. The create page defaults to X-Large, which the demo does not need: the Free Edition warehouse was a 2X-Small (docs/PLAN.md section 2), and ai_parse_document read a 131-page PAD on it in 129 seconds (docs/day-one-results.md, test 3). Sources: https://learn.microsoft.com/en-us/azure/databricks/compute/serverless/, https://learn.microsoft.com/en-us/azure/databricks/admin/sql/serverless and https://learn.microsoft.com/en-us/azure/databricks/compute/sql-warehouse/create
3. Apps. Nothing to turn on. A Premium workspace in a listed region has them, up to 100 per workspace. Where: Compute, then Apps. Command 4 in section 5 makes the app strata there. Sources: https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/ and https://learn.microsoft.com/en-us/azure/databricks/resources/limits
4. Genie's AI setting. Where: click your username at the top right, then Settings, then under Workspace admin the Advanced tab. The toggle is "Partner-powered AI features". It is on by default in a workspace without the compliance security profile, and Genie's chat is not available without it. The account-level switch is in the account console under Settings, the Feature enablement tab, "Enable partner-powered AI features". Sources: https://learn.microsoft.com/en-us/azure/databricks/databricks-ai/partner-powered and https://learn.microsoft.com/en-us/azure/databricks/genie-agents/set-up
5. Lakebase, optional. Where: the app switcher at the top right, then Lakebase Postgres. It is generally available on Azure since March 2, 2026, in the regions in step 4 of the Basics tab and ten more. The App deploy makes a database instance named strata-state at capacity CU_1 through the SDK's database instances API (ops/app/app_live.py, app_state_database). The Lakebase release notes say an instance made through that API is created with autoscaling and scale-to-zero, and suspends after 24 hours without activity (section 7, item 3). I could not confirm that the instance API the deploy calls is offered in every region. If the deploy cannot make or start the instance, it says why and deploys the App without app state, and planning a package then says there is no data service (ops/app/deploy_app.py; src/strata/server/settings.py). Sources: https://learn.microsoft.com/en-us/azure/databricks/release-notes/lakebase/, https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/manage-projects and https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/get-started
6. Vector search, now called AI Search. Nothing to turn on. It needs Unity Catalog and serverless compute, which you have, and a listed region. Command 2 in section 5 makes the endpoint strata-search inside the workspace; it is not an Azure resource. Source: https://learn.microsoft.com/en-us/azure/databricks/ai-search/ai-search
7. People. Since September 14, 2026 a person you add must be given the entitlements "Workspace access" and "Databricks SQL access" by hand; the users group no longer grants them. Where: Settings, then Identity and access, then Users. This applies to the outside reviewer of wizard stage 11 and to the panel. People who open the App must be in the same Databricks account. Sources: https://learn.microsoft.com/en-us/azure/databricks/release-notes/whats-coming and https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/key-concepts

## 4. Run the wizard

The wizard writes the main checkout's .env, saves two of the App's secrets in the Databricks secret scope strata, and writes docs/day-one-results.md (ops/wizard/strata-setup.sh, the header). It has 13 stages. On a second run, Enter keeps each saved value. That is what you want for the Azure stages, and the opposite of what you want for the Databricks ones, so type the new values there.

Two things come before the wizard.

1. Sign the Databricks CLI in to the new workspace by hand. Stage 4 does nothing when the profile strata still answers, and that profile still points at the old host. The CLI (1.22.1 on October 26, 2026) refuses to move a profile to a new host: the sign-in with the new address and `--profile strata` stops with "--profile "strata" has host ..., which conflicts with --host". So first rename the old profile's section in `~/.databrickscfg`, then sign in, which makes a new section named strata:

   ```
   sed -i '' 's/^\[strata\]$/[strata-free-edition]/' ~/.databrickscfg
   databricks auth login --host $DATABRICKS_HOST --profile $PROFILE
   ```

   The old section keeps its host under the name strata-free-edition; its token cache shows as not valid, because the cache is keyed by the profile name, and a fresh sign-in restores it when you switch back (section 9). Then set `default_profile = strata` under `[__settings__]` in the same file, so a CLI command run by hand without `-p` goes to the new workspace too (the repo's own scripts ignore the config file since ticket 82).

   with the new address in place of $DATABRICKS_HOST and strata in place of $PROFILE (names.oauth_profile in ops/dayone/dayone.toml). A browser window opens; sign in. The probes for tests 1 and 10, the demo-ready command and every -p strata command in docs/workspace-catchup.md use this profile.
2. Check the catalog name for the probes. The probes keep their schema, volume, table and index in a catalog named workspace (ops/dayone/dayone.toml lines 26 to 29). If the new workspace's own catalog has another name, change workspace to that name in those four lines before stage 13, or ask the second session to.

Then, in your own terminal, from the main checkout:

```
bash ops/wizard/strata-setup.sh
```

Stage by stage. The stage names are the wizard's.

1. Stage 1, "Your Databricks workspace and a personal access token (test 7)". Databricks side, new value. Type the new address; Enter would keep the old one. Then type the new token too: on October 26, 2026 the wizard kept the saved Free Edition token when Enter was pressed, the probes failed on the new host, and the user had to put the new token into the environment file by hand. The wizard opens the workspace and walks you through making it: Settings, Developer, Access tokens, Manage, Generate new token, named strata, for 90 days. The docs now add one step the wizard does not mention: "Select a scope type and add API scopes", with "BI Tools" or "Other APIs". Strata's scripts call the SQL statements, Genie, AI Search, Apps, Jobs, secrets and Unity Catalog APIs, so a BI Tools token is not enough; pick Other APIs with the widest set the page offers. I could not confirm from the docs whether a token for all APIs is still offered. Each token is valid for one workspace only. Source: https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/pat
2. Stage 2, "The Databricks SQL warehouse". Databricks side, new value. The wizard lists the warehouses with the CLI. On a first run with exactly one warehouse, Enter takes it. On a second run the environment file already holds the Free Edition warehouse's id, and Enter keeps that saved value, so type the new warehouse's id instead (strata-75 hit this on October 26, 2026). With more than one warehouse, it opens the warehouses page, and the id is the last part of the address after /sql/warehouses/. It also keeps AI_SEARCH_ENDPOINT at strata-search.
3. Stage 3, "A Genie space for test 5". Databricks side, new value. The wizard opens the Genie page and says to click New and pick the table samples.nyctaxi.trips. The sidebar item is now called Genie Agents. I could not confirm that samples.nyctaxi.trips exists in a new paid workspace, or that the address the wizard opens still lands on that page. If the table is not offered, pick any table you see; the space is a throwaway. If you cannot make one, press Enter to keep the old id. Test 5's probe then fails until command 3 in section 5 adds Strata's own space id, and you run that probe again afterwards with uv run --script ops/dayone/probe_genie.py --env-file .env, the command under test 5 in docs/day-one-results.md. Source: https://learn.microsoft.com/en-us/azure/databricks/genie-agents/set-up
4. Stage 4, "A browser sign-in for the Databricks command line". Databricks side. It says there is nothing to do, because you signed in before the wizard. If it opens the sign-in page instead, finish the sign-in.
5. Stage 5, "Your Microsoft Entra sign-in to Azure". Azure side. You are signed in already, so it names your subscription and asks whether it holds WorldBank-demo. Type y; Enter means no. The tenant id comes from az.
6. Stage 6, the Foundry project Strata on wb-strata. Azure side, with one write to Databricks. Press Enter twice to keep the two endpoints. On a first run the wizard reads the API key with az, makes the secret scope strata and saves AZURE_OPENAI_API_KEY in it; on October 26, 2026 a second run that kept the values made no scope and saved nothing on the new workspace, and the day-one probes for the hosts, the traces and the Azure costs failed on the missing scope. So after the wizard, make the scope and save the two secrets by hand, pasting each value when the command asks for it, so no value lands on a command line:

   ```
   databricks secrets create-scope strata -p strata
   databricks secrets put-secret strata AZURE_OPENAI_API_KEY -p strata
   databricks secrets put-secret strata APPLICATIONINSIGHTS_CONNECTION_STRING -p strata
   ```

   The wizard's closing summary lists the same lines under the steps it could not take. Then run the probes of stage 13 again.
7. Stage 7, "Four model deployments, each with a cap (test 8)". Azure side. Press Enter through its steps. The deployments carry over, and the stage asks nothing because test 8 passed.
8. Stage 8, "An Azure budget with email alerts". Azure side. Press Enter; the budget strata-monthly exists.
9. Stage 9, "Application Insights for the app (test 10)". Azure side, with one write to Databricks. Press Enter to keep the connection string. On a first run the wizard saves it in the scope as APPLICATIONINSIGHTS_CONNECTION_STRING; on a second run it does not, so the put-secret line under stage 6 saves it. The App deploy needs it there (ops/app/deploy_app.py). On October 24 the probe app could not start because this key was missing from the scope (docs/day-one-results.md, test 1). Press Enter again at the tracing step; tracing is connected already.
10. Stage 10, "One Foundry evaluation after your Entra sign-in (test 9)". Skipped; test 9 passed.
11. Stage 11, "An outside reviewer in the workspace (test 6)". Databricks side. The results file says the person joined already, on the old workspace, so the wizard skips the invitation and records test 6 as waiting for the App. Invite the person on the new workspace by hand, with the wizard's own steps: Settings, Identity and access, Users, Manage, Add user, an outside email you can check. Then give them the two entitlements from section 3, step 7. On Azure, people sign in with Microsoft Entra ID; whether an email outside your tenant can be added without a guest invitation in Entra first is something I could not confirm. The test finishes on the second wizard run, after the App deploy.
12. Stage 12, "Pay-as-you-go before November 10, 2026". Skipped; done on October 24.
13. Stage 13, "The day-one probes". Databricks side. Type y. The probes take about 30 minutes, mostly while Databricks starts the app, the jobs and the AI Search endpoint, and they write tests 1, 2, 3, 4, 5, 8 and 10 in docs/day-one-results.md (ops/dayone/run-probes.sh). Run them now rather than after the App deploy: the hosts probe deploys a small app under the name strata, and once the real App holds that name the probe leaves it alone, so tests 1 and 10 cannot run (ops/dayone/live.py, ensure_probe_app). To run them later, from the main checkout:

    ```
    bash ops/dayone/run-probes.sh --env-file .env
    ```

Which stages can wait: stages 7, 8, 10 and 12 ask nothing. Stage 11 waits for the App. Stage 13 can wait until just before the App deploy, not after it. After the probes, this lists the ten tests with their status:

```
python3 ops/dayone/dayone.py show
```

## 5. The deploy chain

The order comes from this command, which changes nothing and prints the 16 commands below with the resources each one makes:

```
uv run python ops/demo/ready.py --fresh-workspace
```

The order's reasons: the bundle first, since everything reads its catalog; the Genie space before the App, because the space deploy saves the id in the env file and the App deploy writes that id into app.yaml; the App before the job's first run, because the App deploy saves the Azure keys the job's tasks read from the scope (ops/demo/fresh_workspace.py). Every command runs from the main checkout.

Who runs what. Anything that writes a secret is yours: command 4, and the one secret in step 4b. The second session, strata-58, runs the rest from a snapshot with --env-file pointed at the main checkout's .env (docs/workspace-catchup.md, "Running a step from a snapshot"), or you do. The times are from docs/workspace-catchup.md, where it records them.

Command 1, the bundle. Either runs it. On October 26 the first pass ran 00:55 to 00:58 UTC and the second 00:58 to 00:59; the CLI itself runs about three minutes.

```
uv run --script ops/bundle/deploy.py --env-file .env
```

It makes the catalog strata, the schemas bronze, silver, gold and ops, the volume strata.bronze.files, 143 tables, views and metric views, the grants, the four jobs (strata cost pull, strata lesson cross-check, strata nightly, strata retrieval weekly) and the two dashboards. On a workspace without fairshare it prints "I found no catalog named fairshare, so I could not compare it." and exits 0. That is fine. With no App yet it says it granted nothing for the App; also fine.

Command 2, the AI Search endpoint. Either runs it. No minute count is recorded; the endpoint "takes longest to start" (ops/dayone/run-probes.sh).

```
uv run --script ops/dayone/probe_ai_search.py --env-file .env
```

It makes the endpoint strata-search if it is missing and writes test 4. The probes in stage 13 made it already; running this again is harmless.

Command 3, the Genie space. Either runs it. It ran three times after the 00:58 deploy; no minute count.

```
uv run python ops/genie/deploy_space.py --env-file .env
```

It makes the space "Strata: World Bank procurement records" over two metric views, strata.gold.contract_metrics and strata.gold.package_metrics, and the gold table strata.gold.contract_supplier (config/genie.toml), and appends GENIE_SPACE_ID to the env file as its last line; later lines win. Known gap: a second run prints "I updated the space" instead of "No change".

Command 4, the App. You run it, because it writes six secrets. On October 26 the App was created at 05:08:53 UTC, two deployments failed on package installs, which ticket 69 fixed, and the deployment of 06:11:36 succeeded. A redeploy took nine minutes, 10:10 to 10:19 UTC.

```
uv run --script ops/app/deploy_app.py --env-file .env
```

It makes the App strata and its service principal, the Lakebase instance strata-state, the App's resources, scopes, grants and masks, and ends with "Strata is running at https://...". The App answers 502 for about eight and a half minutes after a deploy or restart. The docs give the address the form https://<app-name>-<workspace-id>.<region>.databricksapps.com. Source: https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/key-concepts

Then put the new address in config/urls.toml as app, and write the README's links for the panel from it:

```
uv run python -m strata.proposal readme --write
```

Step 4a. The role that lets the App's agent answer. It is Azure and carries over once assigned; docs/STATUS.md, decision 33, says it is still yours to run. From docs/workspace-catchup.md, ticket 45 step 3, signed in to the subscription:

```
SUB=$(az account show --query id -o tsv)
az role assignment create --assignee c9da9842-0971-4370-992b-40366fdbe42b --role "Cognitive Services User" --scope /subscriptions/$SUB/resourceGroups/WorldBank-demo/providers/Microsoft.CognitiveServices/accounts/wb-strata
```

Step 4b. The cost pull's subscription id goes in the new scope. You run it, because it is a secret, and the command asks for the value:

```
databricks secrets put-secret strata AZURE_SUBSCRIPTION_ID -p strata
```

The App deploy writes FOUNDRY_TENANT_ID itself. The "Cost Management Reader" role was assigned on October 26 and carries over.

Command 5, the nightly job's first run. Either runs it, at any time except around 07:00 UTC, when the scheduled run starts. On October 24 the sixth run took 25 minutes when the document tasks had no work. On October 26, fetch_by_watermark ran 06:41 to 06:55, bronze_to_gold 06:55 to 07:32, and parse_and_embed ran to the 150-minute stop at 09:11.

```
uv run --script ops/bundle/check.py job-run --env-file .env
```

It starts the job strata nightly, waits up to 160 minutes, and checks one row per task in strata.ops.pipeline_runs. What the first run does: fetch_by_watermark fetches every structured source in config/sources.toml into strata.bronze.api_pages: contract awards since FY2020, awards FY2001 to FY2016, IEG ratings, IDA credits and IBRD loans, projects, CPIA and WGI for every country, and the procurement notices and the monthly loan history for the slice's countries only, each country on its own (config/sources.toml; bundle/README.md). That is about 1,900 requests. bronze_to_gold builds silver and gold. parse_and_embed reads documents under a budget: at most 60 minutes of the document host's time a night (ingestion.document_host_minutes in config/thresholds.toml) and at most 500 Route B pages a day across both readers (ingestion.daily_page_cap). So the first night reads part of the document slice, and later nights read the rest. sync_index then syncs strata.gold.passage_index on strata-search. If the run stops at 150 minutes, run the command again; bronze keeps each page, and the watermark counts only fetches that finished. The tasks read the six keys that command 4 wrote to the scope.

Step 5a. The passages and the index in one go, instead of over several nights. Either runs it, outside the nightly window of 03:00 to 05:30 in Washington, 07:00 to 09:30 UTC. On October 26 it wrote 1,028 passages from 23 documents between 12:02 and 12:45 UTC before the daily limit stopped it.

```
uv run --script ops/documents/run_live.py --env-file .env
```

Commands 6 to 14, the nine Foundry agents. Either runs them; they are not timed. They are Azure only: nothing in an agent's definition names the workspace, so the agents carry over, and these runs confirm it. Adding --check to a command reports without changing anything (ops/agent/sync.py).

```
uv run --script ops/agent/sync.py --env-file .env --agent orchestrator
uv run --script ops/agent/sync.py --env-file .env --agent review_notes_writer
uv run --script ops/agent/sync.py --env-file .env --agent mission_brief_writer
uv run --script ops/agent/sync.py --env-file .env --agent ppsd_rows_writer
uv run --script ops/agent/sync.py --env-file .env --agent ppsd_rows_agency_writer
uv run --script ops/agent/sync.py --env-file .env --agent project_paper_writer
uv run --script ops/agent/sync.py --env-file .env --agent package_reader
uv run --script ops/agent/sync.py --env-file .env --agent lesson_review_writer
uv run --script ops/agent/sync.py --env-file .env --agent criteria_reader
```

Command 15, the examples for the reviewing panel. It has never run on any workspace, and it can wait until the panel is named.

```
uv run python -m strata.seed_examples --env-file .env
```

It needs the panel's people in config/roles.toml, each with a user_id, and DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET of the App's service principal in the env file (docs/workspace-catchup.md, ticket 41 step 2). Both are yours to add: the roles file through the gate, and the secret in the env file. The Azure account is a different Databricks account from the Free Edition one, so expect new user ids; the wizard's test 7 evidence line prints your own. Then either runs the command.

Command 16, the demo-ready command. Either runs it. About two minutes when the App is running, 12:45:28 to 12:47:31 UTC on October 26; about ten when it restarts the App.

```
uv run --with databricks-sdk==0.156.0 python ops/demo/ready.py --env-file .env
```

It needs the env file, az signed in, the CLI profile strata and data/out/fixture.duckdb. Its six steps: it starts the App if it is stopped and waits for /api/health; it warms the warehouse and Genie; it asks one smoke question through /api/ask; it rechecks the P156634 signals against the fixture; it runs the seed command; it lists what changed. Its last line is "Strata is ready for the demo." with exit 0 when every step passed. Otherwise it names each failed step, such as "Strata is not ready for the demo. This step failed: the smoke question.", and exits 1 (README.md, "Before a demo").

Then the second wizard run finishes test 6. Run bash ops/wizard/strata-setup.sh again, press Enter through the saved values, and at stage 11 give the reviewer Can use on the App's Permissions page and open the App as that person.

## 6. What carries over, what is made again, what is lost

Carries over with no work, all in Azure: the Foundry project Strata on wb-strata, the nine agents and the guardrail strata-guardrail; the four model deployments and their caps; the Application Insights resource and its connection string; the budget strata-monthly and the pay-as-you-go subscription; the Entra app registration strata-app with its roles; and the seven Azure keys in the env file, FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_TENANT_ID, FOUNDRY_CLIENT_ID, FOUNDRY_CLIENT_SECRET, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and APPLICATIONINSIGHTS_CONNECTION_STRING. AI_SEARCH_ENDPOINT is only a name, strata-search, and stays as it is.

Made again, all in Databricks, by the wizard or one of the 16 commands: the four Databricks keys, DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID and GENIE_SPACE_ID, and the CLI profile strata; the secret scope strata with its keys; the catalog, schemas, volume, tables, grants, jobs and dashboards; the endpoint strata-search; the Genie space, with a new id; the App, with a new service principal and a new address, its resources, grants and masks, and the Lakebase instance strata-state; the rows of bronze, silver, gold and ops, and the index; the workspace's users and groups, which are the outside reviewer, the panel, the staff group and the group strata-team-kenya-water that config/roles.toml names; the App address in config/urls.toml and README.md; and the MLflow experiments and registered models from the backtests, when you run those again.

Lost, unless you copy it by hand, because no script in the repo copies rows between workspaces: app state in Lakebase, which is planned packages and their saves, plan checks opened, criteria checks, risk selections, plan date choices and step start dates (docs/app-state.md); the rows people made in strata.ops, which are drafts and their states, exports and files, follows, uploads and upload rows, disagreement choices, supplier decisions and labels, the lesson review record, lesson visits, passage reports and grades, viewer settings and the seeded examples; the logs in strata.ops, which are usage events, agent runs, evidence opened, pipeline runs, quality checks, evaluation results, cost pulls and the data readiness history; the 1,028 passages written on October 26 and every page fetched into bronze, which the job and the documents run fetch again; Genie's conversations and the warehouse's query history; and the day-one results recorded on the old workspace, whose evidence names the old host.

To get the day-one results again: the probes rewrite each test's block when they run (ops/dayone/dayone.py), so stage 13 of the wizard, or the run-probes command in section 4, records tests 1, 2, 3, 4, 5, 8 and 10 on the new workspace. The wizard's stage 1 records test 7, and its stage 11 records test 6 on the second run. Tests 8 and 9 are Azure facts and stay true. Commit docs/day-one-results.md on build/strata after a run, as that document asks.

## 7. Costs in plain terms

1. Who pays. The Azure subscription, for the compute you use, per second, counted in DBUs. A DBU is Databricks' unit of processing power for pricing. The rates per product are on the Azure pricing page, which I could not open: https://azure.microsoft.com/en-us/pricing/details/databricks/. Sources: https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-trial-vs-free-edition, https://learn.microsoft.com/en-us/azure/databricks/admin/account-settings/serverless-quotas and https://www.databricks.com/product/azure-pricing
2. What stops by itself. The SQL warehouse stops after its Auto stop minutes, 10 by default for serverless and 5 at the least in the UI; an idle warehouse keeps charging until it stops. A stopped App costs nothing; a running Medium App, the default size, is 0.5 DBU an hour. A query on a serverless notebook is canceled after 2.5 hours, the default execution timeout, and the nightly job stops after 150 minutes (bundle/nightly.yml). Sources: https://learn.microsoft.com/en-us/azure/databricks/compute/sql-warehouse/create, https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/key-concepts, https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/compute-size, https://learn.microsoft.com/en-us/azure/databricks/compute/serverless/notebooks and https://learn.microsoft.com/en-us/azure/databricks/admin/usage/
3. Lakebase. On Azure, the instance strata-state that the App deploy makes through the Database instance API (ops/app/app_live.py, capacity CU_1) is created with autoscaling and scale-to-zero. The release note of March 12, 2026 says this holds for instances made through the UI, the Database instance API, Terraform or the SDKs, and the note of May 13, 2026 says a new instance suspends after 24 hours without activity by default. So it does not run all the time. The App deploy starts it again when it finds it stopped (ops/app/app_live.py, app_state_database). Every Provisioned instance moved to the autoscaling platform in July 2026. I found no price for it on the pages I read. Snapshot storage has been billed since June 1, 2026. Sources: https://learn.microsoft.com/en-us/azure/databricks/release-notes/lakebase/ and https://learn.microsoft.com/en-us/azure/databricks/oltp/instances/
4. Genie. Use by people is free through January 31, 2027; use by service principals is billed. Strata's App forwards each viewer's own token to Genie (ops/app/deploy_app.py, the dashboards.genie scope), and the demo-ready command asks as the env file's token, which is yours, so the demo's Genie questions fall under the free use. Source: https://learn.microsoft.com/en-us/azure/databricks/genie/
5. The budget. config/budget.toml sets the free credit at US$197 until November 10, 2026, then a monthly budget of US$50 named strata-monthly, with email alerts at 50, 80 and 100 percent of actual spend and 100 percent of the forecast. Wizard stage 8 made it at subscription scope. Databricks bills through the subscription, so that budget already covers the workspace. A budget only sends email; it stops nothing. Cost data arrives 8 to 24 hours later, and budgets are checked against it every 24 hours. The brakes that stop spend are the caps: tokens per minute on each deployment and the daily cap on Application Insights, both Azure side and carried over, plus the auto stops above. Source: https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets
6. Where to see the spend. Cost analysis in the portal, filtered by the workspace's tags; the account's Usage page in Databricks; and system.billing.usage, which lands within about 12 hours with the app, warehouse and job ids. The Governance page's Azure spend counter reads WorldBank-demo through the daily cost pull once AZURE_SUBSCRIPTION_ID is in the scope (step 4b). Sources: https://learn.microsoft.com/en-us/azure/databricks/admin/account-settings/usage-detail-tags, https://learn.microsoft.com/en-us/azure/databricks/admin/usage/ and https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/billing
7. The limits that go away. Free Edition has a daily quota, and past it "your workspace's compute resources will be shut down and unavailable for the rest of the day", which is what stopped the job compute, Genie, the warehouse and the App between 12:43 and 12:57 UTC on October 26 (docs/STATUS.md, decision 47). It also allows one 2X-Small warehouse, five job tasks at a time, three apps that stop 24 hours after each start, one AI Search endpoint and one Lakebase project. A paid workspace has no daily quota. Its limits are counts, such as 100 apps, 1,000 SQL warehouses and 12,000 saved jobs per workspace, and a serverless quota in DBUs per hour that caps how much runs at once, never stops a running warehouse, and is raised through an Azure support request. No Learn page I read says a paid workspace stops an App on a 24-hour timer; the demo-ready command restarts an App started 12 or more hours ago either way (config/thresholds.toml, [demo_ready] restart_after_hours). Sources: https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-edition-limitations, https://learn.microsoft.com/en-us/azure/databricks/resources/limits and https://learn.microsoft.com/en-us/azure/databricks/admin/account-settings/serverless-quotas
8. If you picked Hybrid. The managed VNet comes with a NAT gateway, which "incurs additional cost". Whether it bills while no classic compute runs is something I did not check. Its charges land in the managed resource group, outside WorldBank-demo, so the Governance page would not count them. Source: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/secure-cluster-connectivity

## 8. If something goes wrong

1. No metastore in the region. The sign: the Metastore column in the account console is empty, Catalog shows no catalog, or the bundle deploy fails on the catalog. The fix: in the account console, open Catalog, click Create metastore, give it a name and the workspace's region, leave the storage path empty, then open its Workspaces tab, click Assign to workspace, pick the workspace, click Assign, then Enable. One metastore per region. You need the account admin role, and the first account admin must be an Entra Global Administrator at first login. Sources: https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/create-metastore and https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/enable-workspaces
2. Apps not available in the region. The sign: Compute has no Apps item, or the App deploy fails when it makes the app. There is no switch to turn on. Apps need Premium and a region with a tick in the Apps column. The fix: make the workspace again in a region from the list in section 2, and delete the first one from the portal, which also removes its managed resource group. Sources: https://learn.microsoft.com/en-us/azure/databricks/resources/feature-region-support and https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/create-workspace
3. Lakebase not available. The sign: the App deploy prints "I could not make or start the Lakebase instance strata-state" with the reason, then goes on. The App runs without app state, so planning a package says there is no data service, and everything else works. The fix: a region on Lakebase's list, or go on without packages for the demo and run the App deploy again later with --keep-secrets, which a session may run. Source: https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/manage-projects
4. Genie says its AI features are off. The sign: the Genie page says chat is not available, or the Genie probe fails. The fix: click your username, Settings, Workspace admin, the Advanced tab, and turn "Partner-powered AI features" on. If the account enforces it off, open the account console, Settings, the Feature enablement tab, and turn "Enable partner-powered AI features" on. Source: https://learn.microsoft.com/en-us/azure/databricks/databricks-ai/partner-powered
5. The bundle cannot create the catalog strata. This happened on October 24 on Free Edition: the metastore had no storage root and used default storage, and the CLI failed with INVALID_STATE. The fix the repo used: run CREATE CATALOG IF NOT EXISTS strata on the SQL warehouse, then bind the catalog to the bundle with the CLI signed in to the new host, then run the deploy again (docs/workspace-catchup.md, ticket 04 step 1; bundle/README.md).

   ```
   databricks bundle deployment bind strata strata
   ```

   A metastore made for you has no managed storage root. If the warehouse answers that a catalog needs a managed location, that is extra setup, a storage account and an external location, which this guide does not cover. Source: https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/manage-metastore
6. The App cannot start because a secret is missing from the scope, such as "Invalid secret resource appinsights". Wizard stage 9 writes that one; a deploy without --keep-secrets writes the six Azure keys; and any other key is written as you with the command README.md names, which asks for the value:

   ```
   databricks secrets put-secret strata <name>
   ```

7. The probes or the demo-ready command cannot reach the App's health route, though the App runs. The CLI profile strata still points at the old host. Run the sign-in command in section 4 again with the new address.

## 9. Switching back

Two commands in your own terminal, from the main checkout:

```
cp .env .env.azure
cp .env.free-edition .env
```

Every live command reads the env file --env-file names, and the main checkout's .env is the default (ops/dayone/dayone.py; ops/bundle/workspace_env.py), so the old workspace comes back with the second copy. Two things sit outside the env file. The CLI profile strata points at one host, and the CLI refuses to move it, so rename the sections in `~/.databrickscfg` (strata to strata-azure, then strata-free-edition to strata) and run the sign-in command from section 4 with the old address, https://dbc-b5ef314b-b0cd.cloud.databricks.com, which refreshes that profile's token. The old workspace's bundle state moved to serial 25 on October 26, 2026, when a deploy landed there by mistake (ticket 82); nothing was created, and the next deploy there reads that state. And config/urls.toml holds the App address, so put the old one back, https://strata-7474658003099155.aws.databricksapps.com, and run the readme command from section 5, step 4. The old workspace keeps everything it holds: nothing in the repo deletes a workspace object, and rows leave only through a DELETE with a WHERE (CLAUDE.md rule 5). The daily limit still applies there. The Azure env file carries the GENIE_SPACE_ID lines the space deploy appended, and the last one is the one in use.

## Sources

Azure and Databricks pages, all read on October 26, 2026:

- https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/
- https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/create-workspace
- https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/serverless-workspaces
- https://learn.microsoft.com/en-us/azure/databricks/admin/account-settings/standard-tier
- https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-trial
- https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-trial-vs-free-edition
- https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-edition-limitations
- https://learn.microsoft.com/en-us/azure/databricks/resources/feature-region-support
- https://learn.microsoft.com/en-us/azure/databricks/resources/limits
- https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/overview
- https://learn.microsoft.com/en-us/cli/azure/databricks/workspace?view=azure-cli-latest
- https://learn.microsoft.com/en-us/azure/databricks/release-notes/whats-coming
- https://learn.microsoft.com/en-us/azure/databricks/storage/default-storage
- https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/secure-cluster-connectivity
- https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/vnet-inject
- https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/private-link-standard
- https://learn.microsoft.com/en-us/azure/databricks/security/network/front-end/front-end-private-connect
- https://learn.microsoft.com/en-us/azure/databricks/security/network/front-end/ip-access-list-workspace
- https://learn.microsoft.com/en-us/azure/databricks/security/network/concepts/privatelink-concepts
- https://learn.microsoft.com/en-us/azure/databricks/admin/sql/serverless
- https://learn.microsoft.com/en-us/azure/databricks/security/keys/
- https://learn.microsoft.com/en-us/azure/databricks/security/privacy/enhanced-security-compliance
- https://learn.microsoft.com/en-us/azure/databricks/security/privacy/enhanced-security-monitoring
- https://learn.microsoft.com/en-us/azure/databricks/admin/account-settings/usage-detail-tags
- https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/pat
- https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/get-started
- https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/setup-uc
- https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/create-metastore
- https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/enable-workspaces
- https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/manage-metastore
- https://learn.microsoft.com/en-us/azure/databricks/compute/serverless/
- https://learn.microsoft.com/en-us/azure/databricks/compute/sql-warehouse/create
- https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/
- https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/key-concepts
- https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/compute-size
- https://learn.microsoft.com/en-us/azure/databricks/databricks-ai/partner-powered
- https://learn.microsoft.com/en-us/azure/databricks/genie/
- https://learn.microsoft.com/en-us/azure/databricks/genie-agents/set-up
- https://learn.microsoft.com/en-us/azure/databricks/release-notes/lakebase/
- https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/manage-projects
- https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/get-started
- https://learn.microsoft.com/en-us/azure/databricks/oltp/instances/
- https://learn.microsoft.com/en-us/azure/databricks/ai-search/ai-search
- https://learn.microsoft.com/en-us/azure/databricks/admin/account-settings/serverless-quotas
- https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/billing
- https://learn.microsoft.com/en-us/azure/databricks/admin/usage/
- https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets
- https://www.databricks.com/product/azure-pricing
- https://azure.microsoft.com/en-us/pricing/details/databricks/ (not opened; the DBU rates and the add-on price come from search snippets)

Repo files the commands and facts come from:

- ops/wizard/strata-setup.sh (the wizard, its stages and the sign-in command it prints)
- ops/dayone/run-probes.sh, ops/dayone/dayone.toml, ops/dayone/dayone.py, ops/dayone/live.py, ops/dayone/probe_ai_search.py (the probes)
- ops/demo/ready.py and ops/demo/fresh_workspace.py (the 16 commands and the demo-ready command)
- ops/bundle/deploy.py, ops/bundle/check.py, ops/bundle/bundle_live.py, bundle/README.md, databricks.yml, bundle/nightly.yml (the bundle and the nightly job)
- ops/genie/deploy_space.py and config/genie.toml (the Genie space and what it reads)
- ops/app/deploy_app.py and ops/app/app_live.py (the App and the Lakebase instance)
- ops/agent/sync.py (the Foundry agents)
- ops/documents/run_live.py (the documents run)
- src/strata/seed_examples.py, config/roles.toml, config/examples.toml (the examples for the panel)
- config/budget.toml, config/thresholds.toml, config/urls.toml, config/models.toml, .env.example, .gitignore
- README.md, docs/day-one-results.md, docs/workspace-catchup.md, docs/STATUS.md, docs/app-state.md, docs/PLAN.md, CLAUDE.md
- The research notes beside this guide: research-notes.md in the same folder
