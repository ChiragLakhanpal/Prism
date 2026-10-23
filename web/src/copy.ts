// Every string a person reads in the web shell, in one place (DESIGN.md section 7).
// The design-system ticket makes this the only home of user-facing copy and adds its lint.

export const copy = {
  appName: "Strata",
  skipLink: "Skip to the main content",
  // DESIGN.md section 8, word for word.
  footer:
    "Strata is an independent demo built on World Bank open data. It is not a World Bank product, " +
    "and the World Bank has not reviewed or endorsed it.",
  viewer: {
    checking: "Checking who you are.",
    signedIn: (name: string) => `You are signed in as ${name}.`,
    signedOut: "You are not signed in. Open Strata through its Databricks App to sign in.",
    unreachable: "I can't reach Strata's server. Try again in a minute.",
  },
} as const;
