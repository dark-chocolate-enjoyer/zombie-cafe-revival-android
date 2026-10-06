package serialization

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"

	"file_types"
)

// Fail-closed contract for the JP serializers: malformed JSON (or an empty
// record list) must return an error and produce no bytes, and the file-level
// pack path must neither create nor truncate the output binary.

var jpSerializers = map[string]func(string) ([]byte, error){
	"characterData.bin.mid": SerializeCharactersJP,
	"foodData.bin.mid":      SerializeFoodJP,
	"furnitureData.bin.mid": SerializeFurnitureJP,
	"quest.bin.mid":         SerializeQuestsJP,
	"item sets":             SerializeItemSets,
	"placement layouts":     SerializePlacementLayouts,
	"enemy item data":       SerializeEnemyItemData,
}

func TestJPSerializersRejectBadInput(t *testing.T) {
	badInputs := map[string]string{
		"truncated json":     `[{"Name": "half a rec`,
		"not json":           `this is not json at all`,
		"wrong shape":        `{"Name": "object, not array"}`,
		"wrong element type": `[12345]`,
		"null":               `null`,
		"empty array":        `[]`,
		"empty string":       ``,
	}
	for name, serialize := range jpSerializers {
		for label, input := range badInputs {
			encoded, err := serialize(input)
			if err == nil {
				t.Errorf("%s: %s: expected error, got %d bytes", name, label, len(encoded))
			}
			if encoded != nil {
				t.Errorf("%s: %s: expected nil output on error, got %d bytes", name, label, len(encoded))
			}
		}
	}
}

func TestJPSerializersAcceptValidInput(t *testing.T) {
	valid := map[string]string{
		"characterData.bin.mid": `[{"Name": "テスト", "Category": "test", "CharacterArtString": "test", "HumanDescription": "h", "ZombieDescription": "z"}]`,
		"foodData.bin.mid":      `[{"Name": "テスト料理", "Price": 5}]`,
		"furnitureData.bin.mid": `[{"Name": "テスト家具", "Color": [0, 0, 0, 0], "Description": "d"}]`,
		"quest.bin.mid":         `[{"QuestID": 0, "Text": "現金を[NUM]＄貯めろ。"}]`,
		"item sets":             `[{"Name":"test","Slots":["","","","","","","","","","","","","","","",""]}]`,
		"placement layouts":     `[{"Type":"","A":0,"B":1,"C":2}]`,
		"enemy item data":       `[[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]]`,
	}
	for name, serialize := range jpSerializers {
		encoded, err := serialize(valid[name])
		if err != nil {
			t.Errorf("%s: valid single-record input rejected: %v", name, err)
			continue
		}
		if len(encoded) == 0 {
			t.Errorf("%s: valid input produced no bytes", name)
		}
	}
}

func TestJPSerializersRejectWrongFixedWidths(t *testing.T) {
	tests := map[string]struct {
		serialize func(string) ([]byte, error)
		input     string
	}{
		"furniture color": {
			SerializeFurnitureJP,
			`[{"Name":"bad","Color":[0,0,0],"Description":"d"}]`,
		},
		"item slots short": {
			SerializeItemSets,
			`[{"Name":"bad","Slots":[""]}]`,
		},
		"item slots long": {
			SerializeItemSets,
			`[{"Name":"bad","Slots":["","","","","","","","","","","","","","","","",""]}]`,
		},
		"enemy row short": {
			SerializeEnemyItemData,
			`[[0]]`,
		},
		"enemy row long": {
			SerializeEnemyItemData,
			`[[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]]`,
		},
	}
	for name, test := range tests {
		encoded, err := test.serialize(test.input)
		if err == nil {
			t.Errorf("%s: expected error, got %d bytes", name, len(encoded))
		}
		if encoded != nil {
			t.Errorf("%s: expected nil output on error, got %d bytes", name, len(encoded))
		}
	}
}

func TestSerializeFilesJPFailsClosed(t *testing.T) {
	inDir, outDir := t.TempDir(), t.TempDir()

	// quest: malformed JSON, with a pre-existing output binary that must
	// survive untouched.
	if err := os.WriteFile(filepath.Join(inDir, "quest.bin.mid.json"),
		[]byte(`[{"QuestID": 0, "Text": "broken`), 0644); err != nil {
		t.Fatal(err)
	}
	preexisting := []byte("PRE-EXISTING BINARY CONTENT")
	if err := os.WriteFile(filepath.Join(outDir, "quest.bin.mid"), preexisting, 0644); err != nil {
		t.Fatal(err)
	}

	// food: malformed JSON with NO pre-existing output — nothing may be created.
	if err := os.WriteFile(filepath.Join(inDir, "foodData.bin.mid.json"),
		[]byte(`not json`), 0644); err != nil {
		t.Fatal(err)
	}

	// characters: valid JSON — must still be written despite the failures above.
	if err := os.WriteFile(filepath.Join(inDir, "characterData.bin.mid.json"),
		[]byte(`[{"Name": "テスト", "Category": "c", "CharacterArtString": "a", "HumanDescription": "h", "ZombieDescription": "z"}]`), 0644); err != nil {
		t.Fatal(err)
	}

	failed := SerializeFilesJP(inDir, outDir)
	if failed != 2 {
		t.Errorf("failed count = %d, want 2", failed)
	}

	got, err := os.ReadFile(filepath.Join(outDir, "quest.bin.mid"))
	if err != nil {
		t.Fatalf("pre-existing quest.bin.mid unreadable after failed pack: %v", err)
	}
	if !bytes.Equal(got, preexisting) {
		t.Errorf("pre-existing quest.bin.mid was modified by a failed pack (len %d -> %d)",
			len(preexisting), len(got))
	}

	if _, err := os.Stat(filepath.Join(outDir, "foodData.bin.mid")); !os.IsNotExist(err) {
		t.Errorf("foodData.bin.mid was created from malformed JSON (stat err: %v)", err)
	}

	charOut, err := os.ReadFile(filepath.Join(outDir, "characterData.bin.mid"))
	if err != nil {
		t.Fatalf("valid characterData.bin.mid was not written: %v", err)
	}
	chars := file_types.ReadCharactersJP(bytes.NewReader(charOut))
	if len(chars) != 1 || chars[0].Name != "テスト" {
		t.Errorf("written characterData.bin.mid decodes to %d records", len(chars))
	}
}

func TestSerializeFilesPropagatesJPFailures(t *testing.T) {
	inDir, outDir := t.TempDir(), t.TempDir()
	if err := os.WriteFile(
		filepath.Join(inDir, "quest.bin.mid.json"),
		[]byte(`not json`),
		0644,
	); err != nil {
		t.Fatal(err)
	}

	if failed := SerializeFiles(inDir, outDir, true); failed != 1 {
		t.Errorf("SerializeFiles failure count = %d, want 1", failed)
	}
}
