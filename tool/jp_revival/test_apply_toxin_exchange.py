import copy
import unittest

import apply_toxin_exchange as toxin


def vanilla_furniture():
    records = [{} for _ in range(835)]
    for exchange in toxin.EXCHANGES:
        records[exchange["index"]] = {
            "Name": "source",
            "Price": exchange["source_price"],
            "PurchaseWithToxin": True,
            "Type": 10,
            "BuyMoneyAmount": exchange["source_amount"],
            "Description": "source",
        }
    return records


class NativePatchTests(unittest.TestCase):
    def test_replaces_only_verified_type10_block(self):
        source = bytearray(toxin.PATCH_OFFSET + len(toxin.ORIGINAL_TYPE10_BLOCK) + 8)
        source[toxin.PATCH_OFFSET : toxin.PATCH_OFFSET + 12] = (
            toxin.ORIGINAL_TYPE10_BLOCK
        )

        patched = toxin.patch_native_library(bytes(source), verify_hash=False)

        self.assertEqual(
            patched[toxin.PATCH_OFFSET : toxin.PATCH_OFFSET + 12],
            toxin.PATCHED_TYPE10_BLOCK,
        )
        self.assertEqual(patched[: toxin.PATCH_OFFSET], source[: toxin.PATCH_OFFSET])
        self.assertEqual(
            patched[toxin.PATCH_OFFSET + 12 :],
            source[toxin.PATCH_OFFSET + 12 :],
        )

    def test_rejects_unexpected_native_bytes(self):
        source = bytes(toxin.PATCH_OFFSET + len(toxin.ORIGINAL_TYPE10_BLOCK))
        with self.assertRaises(toxin.PatchError):
            toxin.patch_native_library(source, verify_hash=False)


class FurniturePatchTests(unittest.TestCase):
    def test_converts_the_four_vanilla_cash_packs(self):
        source = vanilla_furniture()
        before = copy.deepcopy(source)

        patched = toxin.patch_furniture(source)

        self.assertEqual(source, before)
        for exchange in toxin.EXCHANGES:
            record = patched[exchange["index"]]
            self.assertEqual(record["Name"], exchange["name"])
            self.assertEqual(record["Price"], exchange["price"])
            self.assertFalse(record["PurchaseWithToxin"])
            self.assertEqual(record["BuyMoneyAmount"], exchange["amount"])

    def test_rejects_non_vanilla_exchange_row(self):
        records = vanilla_furniture()
        records[182]["Price"] = 999
        with self.assertRaises(toxin.PatchError):
            toxin.patch_furniture(records)

    def test_rejects_numeric_boolean_audit_snapshot(self):
        records = vanilla_furniture()
        records[182]["PurchaseWithToxin"] = 1
        with self.assertRaises(toxin.PatchError):
            toxin.patch_furniture(records)

    def test_rejects_wrong_record_count(self):
        with self.assertRaises(toxin.PatchError):
            toxin.patch_furniture(vanilla_furniture()[:-1])


if __name__ == "__main__":
    unittest.main()
