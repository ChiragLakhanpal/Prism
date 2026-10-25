"""Check your criteria: section 5 of the package workspace (ticket 31).

reading.py finds the item registry's items (config/criteria_items.toml) in a notice's text, an award notice's
rejection reasons and the parts a requirement measures, and compares a notice's requirement with yours. The
tools compare_criteria and rejected_bids (src/strata/tools) and the check-your-criteria workflow (workflow.py)
all read text through it, so an item is found the same way everywhere. store.py keeps the pasted text and the
results in the app state store, readable only by their owner.
"""
