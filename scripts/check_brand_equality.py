import sys
sys.path.insert(0, ".")
from productiq_catalog.ground_truth.ingest import GroundTruthStore
from productiq_catalog.lookups.loader import ManufacturerBrandLookup

gt = GroundTruthStore()
rec1 = gt.get_by_row_id(1)
print("GT Rec 1 expected_brand:", repr(rec1.expected_brand))
rec2 = gt.get_by_row_id(2)
print("GT Rec 2 expected_brand:", repr(rec2.expected_brand))

lookup = ManufacturerBrandLookup()
b0 = lookup.get_all_mappings()[0]["canonical_brand"]
b1 = lookup.get_all_mappings()[1]["canonical_brand"]
print("Lookup mapping 0 brand:", repr(b0))
print("Lookup mapping 1 brand:", repr(b1))
print("Equal rec1:", rec1.expected_brand == b0)
print("Equal rec2:", rec2.expected_brand == b1)
