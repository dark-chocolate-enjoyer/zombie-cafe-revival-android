package file_types

import (
	"bytes"
	"strings"
	"testing"
)

// Synthetic safeguard tests — these run everywhere (no JP_DATA_DIR needed).

func TestStringsJPRoundTripSynthetic(t *testing.T) {
	raw := []byte("line0\n\n毒を[NUM]個使う\nRaid # rival cafés\\now")
	lines, err := ReadStringsJP(bytes.NewReader(raw))
	if err != nil {
		t.Fatal(err)
	}
	if len(lines) != 4 {
		t.Fatalf("line count = %d, want 4", len(lines))
	}
	var out bytes.Buffer
	if err := WriteStringsJP(&out, lines); err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(raw, out.Bytes()) {
		t.Fatalf("round trip not byte-identical: %q -> %q", raw, out.Bytes())
	}
}

func TestStringsJPReadRejectsInvalidUTF8(t *testing.T) {
	if _, err := ReadStringsJP(bytes.NewReader([]byte{'a', 0xFF, 0xFE, 'b'})); err == nil {
		t.Fatal("expected invalid-UTF-8 read to fail")
	}
}

func TestStringsJPReplacementValidation(t *testing.T) {
	original := []string{"現金を[NUM]＄貯めろ。", "", "ライバル店を#店舗襲撃する", "あと\\で再購入可能"}

	ok := []string{"Save up $[NUM] in cash.", "", "Raid # rival cafés", "Buy again\\later"}
	if err := ValidateStringsJPReplacement(original, ok); err != nil {
		t.Fatalf("valid replacement rejected: %v", err)
	}

	cases := map[string][]string{
		"line count changed": {"Save up $[NUM] in cash.", "", "Raid # rival cafés"},
		"placeholder dropped": {"Save up cash.", "", "Raid # rival cafés",
			"Buy again\\later"},
		"placeholder duplicated": {"Save up $[NUM] or [NUM] in cash.", "", "Raid # rival cafés",
			"Buy again\\later"},
		"number slot dropped": {"Save up $[NUM] in cash.", "", "Raid rival cafés",
			"Buy again\\later"},
		"line-break escape dropped": {"Save up $[NUM] in cash.", "", "Raid # rival cafés",
			"Buy again later"},
		"empty line filled": {"Save up $[NUM] in cash.", "oops", "Raid # rival cafés",
			"Buy again\\later"},
		"line emptied": {"Save up $[NUM] in cash.", "", "",
			"Buy again\\later"},
		"carriage return introduced": {"Save up $[NUM] in cash.\r", "", "Raid # rival cafés",
			"Buy again\\later"},
		"invalid utf8 introduced": {"Save up $[NUM] in cash." + string([]byte{0xFF}), "", "Raid # rival cafés",
			"Buy again\\later"},
	}
	for name, updated := range cases {
		if err := ValidateStringsJPReplacement(original, updated); err == nil {
			t.Errorf("%s: expected rejection, got nil", name)
		}
	}

	// The validating writer must refuse to produce any output on error.
	var out bytes.Buffer
	if err := WriteStringsJPReplacement(&out, original, cases["placeholder dropped"]); err == nil {
		t.Fatal("expected validating writer to refuse")
	}
	if out.Len() != 0 {
		t.Fatalf("validating writer wrote %d bytes despite refusing", out.Len())
	}
}

func TestStringsJPValidationReportsAllProblems(t *testing.T) {
	original := []string{"[NUM]個", "#軒", "毒"}
	updated := []string{"no token", "no slot", "Toxin"}
	err := ValidateStringsJPReplacement(original, updated)
	if err == nil {
		t.Fatal("expected rejection")
	}
	for _, want := range []string{"line 0", "line 1"} {
		if !strings.Contains(err.Error(), want) {
			t.Errorf("error should mention %q, got:\n%v", want, err)
		}
	}
}
