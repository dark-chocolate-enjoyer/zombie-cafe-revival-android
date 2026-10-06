package file_types

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// Round-trip gates for the enemy/colosseum formats decoded in pass 4.
// The EN copies ship in the repository (src/assets/data), so those tests
// always run; the JP copies use the JP_DATA_DIR gate like the other JP tests.

func enDataFile(t *testing.T, name string) []byte {
	t.Helper()
	data, err := os.ReadFile(filepath.Join("..", "..", "src", "assets", "data", name))
	if err != nil {
		t.Skipf("EN data file %s not readable: %v", name, err)
	}
	return data
}

func roundTripItemSets(t *testing.T, label string, original []byte) []ItemSet {
	t.Helper()
	sets := ReadItemSets(bytes.NewReader(original))
	var out bytes.Buffer
	WriteItemSets(&out, sets)
	requireIdentical(t, label, original, out.Bytes())

	// JSON leg (the pack/unpack pipeline goes through JSON)
	b, err := json.Marshal(sets)
	if err != nil {
		t.Fatal(err)
	}
	var decoded []ItemSet
	if err := json.Unmarshal(b, &decoded); err != nil {
		t.Fatal(err)
	}
	out.Reset()
	WriteItemSets(&out, decoded)
	requireIdentical(t, label+" (json leg)", original, out.Bytes())
	return sets
}

func roundTripLayouts(t *testing.T, label string, original []byte) []PlacementRecord {
	t.Helper()
	records := ReadPlacementLayouts(bytes.NewReader(original))
	var out bytes.Buffer
	WritePlacementLayouts(&out, records)
	requireIdentical(t, label, original, out.Bytes())

	b, err := json.Marshal(records)
	if err != nil {
		t.Fatal(err)
	}
	var decoded []PlacementRecord
	if err := json.Unmarshal(b, &decoded); err != nil {
		t.Fatal(err)
	}
	out.Reset()
	WritePlacementLayouts(&out, decoded)
	requireIdentical(t, label+" (json leg)", original, out.Bytes())

	// Structural invariant: ""-typed header records partition the list
	// exactly — each header's A counts the placements that follow it.
	for i := 0; i < len(records); {
		if records[i].Type != "" {
			t.Fatalf("%s: expected group header at record %d, got %+v", label, i, records[i])
		}
		n := int(records[i].A)
		if i+1+n > len(records) {
			t.Fatalf("%s: header at %d claims %d items past EOF", label, i, n)
		}
		for j := i + 1; j <= i+n; j++ {
			if records[j].Type == "" {
				t.Fatalf("%s: header found inside group at record %d", label, j)
			}
		}
		i += 1 + n
	}
	return records
}

func roundTripEnemyItemData(t *testing.T, label string, original []byte) {
	t.Helper()
	rows := ReadEnemyItemData(bytes.NewReader(original))
	var out bytes.Buffer
	WriteEnemyItemData(&out, rows)
	requireIdentical(t, label, original, out.Bytes())

	b, err := json.Marshal(rows)
	if err != nil {
		t.Fatal(err)
	}
	var decoded []EnemyItemDataRow
	if err := json.Unmarshal(b, &decoded); err != nil {
		t.Fatal(err)
	}
	out.Reset()
	WriteEnemyItemData(&out, decoded)
	requireIdentical(t, label+" (json leg)", original, out.Bytes())
}

func TestENRoundTripEnemyFiles(t *testing.T) {
	sets := roundTripItemSets(t, "EN enemyItems.bin.mid",
		enDataFile(t, "enemyItems.bin.mid"))
	if len(sets) != 14 {
		t.Fatalf("EN enemyItems record count = %d, want 14", len(sets))
	}
	if sets[0].Name != "Cafe" {
		t.Fatalf("EN enemyItems first record = %q, want Cafe", sets[0].Name)
	}
	roundTripLayouts(t, "EN enemyLayouts.bin.mid",
		enDataFile(t, "enemyLayouts.bin.mid"))
	roundTripEnemyItemData(t, "EN enemyItemData.bin.mid",
		enDataFile(t, "enemyItemData.bin.mid"))
}

func TestJPRoundTripEnemyFiles(t *testing.T) {
	sets := roundTripItemSets(t, "JP enemyItems.bin.mid",
		jpDataFile(t, "enemyItems.bin.mid"))
	if len(sets) != 180 {
		t.Fatalf("JP enemyItems record count = %d, want 180", len(sets))
	}
	roundTripLayouts(t, "JP enemyLayouts.bin.mid",
		jpDataFile(t, "enemyLayouts.bin.mid"))
	roundTripEnemyItemData(t, "JP enemyItemData.bin.mid",
		jpDataFile(t, "enemyItemData.bin.mid"))
}

func TestJPRoundTripColosseumFiles(t *testing.T) {
	sets := roundTripItemSets(t, "JP colosseumItems.bin.mid",
		jpDataFile(t, "colosseumItems.bin.mid"))
	if len(sets) != 1 || sets[0].Name != "Field1" {
		t.Fatalf("JP colosseumItems = %d records (first %q), want the single Field1 stub",
			len(sets), sets[0].Name)
	}
	records := roundTripLayouts(t, "JP colosseumLayouts.bin.mid",
		jpDataFile(t, "colosseumLayouts.bin.mid"))
	if len(records) != 3 {
		t.Fatalf("JP colosseumLayouts flat record count = %d, want 3", len(records))
	}
}
