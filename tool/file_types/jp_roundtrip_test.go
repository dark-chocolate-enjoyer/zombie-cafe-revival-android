package file_types

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// Round-trip gate for the JP 1.7.0 data formats. Point JP_DATA_DIR at an
// extracted JP assets/data directory (scratch copy, never game sources);
// the tests skip when it is unset so the suite stays green without the
// non-committed game files.
//
//	JP_DATA_DIR=/path/to/scratch/assets/data go test -run JPRoundTrip ./...

func jpDataFile(t *testing.T, name string) []byte {
	t.Helper()
	dir := os.Getenv("JP_DATA_DIR")
	if dir == "" {
		t.Skip("JP_DATA_DIR not set; skipping JP round-trip gate")
	}
	data, err := os.ReadFile(filepath.Join(dir, name))
	if err != nil {
		t.Fatalf("reading %s: %v", name, err)
	}
	return data
}

func requireIdentical(t *testing.T, name string, original, reencoded []byte) {
	t.Helper()
	if bytes.Equal(original, reencoded) {
		return
	}
	offset := -1
	limit := len(original)
	if len(reencoded) < limit {
		limit = len(reencoded)
	}
	for i := 0; i < limit; i++ {
		if original[i] != reencoded[i] {
			offset = i
			break
		}
	}
	t.Fatalf("%s: re-encode not byte-identical (len %d -> %d, first diff at offset %d)",
		name, len(original), len(reencoded), offset)
}

func TestJPRoundTripFood(t *testing.T) {
	original := jpDataFile(t, "foodData.bin.mid")
	foods := ReadFoodsJP(bytes.NewReader(original))
	var out bytes.Buffer
	WriteFoodsJP(&out, foods)
	requireIdentical(t, "foodData.bin.mid", original, out.Bytes())
}

func TestJPRoundTripFurniture(t *testing.T) {
	original := jpDataFile(t, "furnitureData.bin.mid")
	furniture := ReadFurnitureDataJP(bytes.NewReader(original))
	var out bytes.Buffer
	WriteFurnitureDataJP(&out, furniture)
	requireIdentical(t, "furnitureData.bin.mid", original, out.Bytes())
}

func TestJPRoundTripCharacters(t *testing.T) {
	original := jpDataFile(t, "characterData.bin.mid")
	characters := ReadCharactersJP(bytes.NewReader(original))
	var out bytes.Buffer
	WriteCharactersJP(&out, characters)
	requireIdentical(t, "characterData.bin.mid", original, out.Bytes())

	// Record 148 carries 10 in the toxin-flag byte; the reader must preserve
	// it as a raw byte rather than panicking the way a bool read would.
	if len(characters) > 148 && characters[148].PurchaseWithToxin != 10 {
		t.Fatalf("record 148 PurchaseWithToxin = %d, want raw byte 10",
			characters[148].PurchaseWithToxin)
	}
}

func TestJPRoundTripQuests(t *testing.T) {
	original := jpDataFile(t, "quest.bin.mid")
	quests := ReadQuestsJP(bytes.NewReader(original))
	var out bytes.Buffer
	WriteQuestsJP(&out, quests)
	requireIdentical(t, "quest.bin.mid", original, out.Bytes())

	// Anchor points from the pass-2 schema report: 1,020 sequential records,
	// record 0 is the level-9 "save up cash" HQ mission.
	if len(quests) != 1020 {
		t.Fatalf("quest count = %d, want 1020", len(quests))
	}
	if quests[0].QuestID != 0 || quests[0].GoalAmount != 10000 || quests[0].RewardXP != 1250 {
		t.Fatalf("record 0 = id %d goal %d xp %d, want id 0 goal 10000 xp 1250",
			quests[0].QuestID, quests[0].GoalAmount, quests[0].RewardXP)
	}
}

func TestJPRoundTripStrings(t *testing.T) {
	original := jpDataFile(t, "strings.bin.mid")
	lines, err := ReadStringsJP(bytes.NewReader(original))
	if err != nil {
		t.Fatal(err)
	}
	var out bytes.Buffer
	if err := WriteStringsJP(&out, lines); err != nil {
		t.Fatal(err)
	}
	requireIdentical(t, "strings.bin.mid", original, out.Bytes())

	if len(lines) != 741 {
		t.Fatalf("strings line count = %d, want 741", len(lines))
	}

	// The identity replacement must pass the safeguard and stay byte-identical.
	out.Reset()
	if err := WriteStringsJPReplacement(&out, lines, lines); err != nil {
		t.Fatal(err)
	}
	requireIdentical(t, "strings.bin.mid (validated write)", original, out.Bytes())
}

// The pack/unpack pipeline goes through JSON, so the JSON leg must also be
// lossless: decode -> JSON -> decode JSON -> re-encode -> byte-identical.
func TestJPRoundTripThroughJSON(t *testing.T) {
	t.Run("food", func(t *testing.T) {
		original := jpDataFile(t, "foodData.bin.mid")
		b, err := json.Marshal(ReadFoodsJP(bytes.NewReader(original)))
		if err != nil {
			t.Fatal(err)
		}
		var foods []FoodJP
		if err := json.Unmarshal(b, &foods); err != nil {
			t.Fatal(err)
		}
		var out bytes.Buffer
		WriteFoodsJP(&out, foods)
		requireIdentical(t, "foodData.bin.mid (json leg)", original, out.Bytes())
	})
	t.Run("furniture", func(t *testing.T) {
		original := jpDataFile(t, "furnitureData.bin.mid")
		b, err := json.Marshal(ReadFurnitureDataJP(bytes.NewReader(original)))
		if err != nil {
			t.Fatal(err)
		}
		var furniture []FurnitureJP
		if err := json.Unmarshal(b, &furniture); err != nil {
			t.Fatal(err)
		}
		var out bytes.Buffer
		WriteFurnitureDataJP(&out, furniture)
		requireIdentical(t, "furnitureData.bin.mid (json leg)", original, out.Bytes())
	})
	t.Run("characters", func(t *testing.T) {
		original := jpDataFile(t, "characterData.bin.mid")
		b, err := json.Marshal(ReadCharactersJP(bytes.NewReader(original)))
		if err != nil {
			t.Fatal(err)
		}
		var characters []CharacterJP
		if err := json.Unmarshal(b, &characters); err != nil {
			t.Fatal(err)
		}
		var out bytes.Buffer
		WriteCharactersJP(&out, characters)
		requireIdentical(t, "characterData.bin.mid (json leg)", original, out.Bytes())
	})
	t.Run("quests", func(t *testing.T) {
		original := jpDataFile(t, "quest.bin.mid")
		b, err := json.Marshal(ReadQuestsJP(bytes.NewReader(original)))
		if err != nil {
			t.Fatal(err)
		}
		var quests []QuestJP
		if err := json.Unmarshal(b, &quests); err != nil {
			t.Fatal(err)
		}
		var out bytes.Buffer
		WriteQuestsJP(&out, quests)
		requireIdentical(t, "quest.bin.mid (json leg)", original, out.Bytes())
	})
}
