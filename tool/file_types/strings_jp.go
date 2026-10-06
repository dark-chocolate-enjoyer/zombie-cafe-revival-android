package file_types

import (
	"fmt"
	"io"
	"strings"
	"unicode/utf8"
)

// strings.bin.mid (JP 1.7.0) is not a length-prefixed binary format: it is a
// single UTF-8 buffer of newline-joined lines with NO trailing newline. The
// engine addresses lines by index, so a translated replacement file must keep
// the exact line count and ordering; losing or gaining a line silently shifts
// every message after it.
//
// ReadStringsJP/WriteStringsJP round-trip the file byte-identically.
// WriteStringsJPReplacement is the only supported way to emit a *modified*
// strings file: it refuses to write when the replacement breaks the line
// count, empties, or the per-line placeholder structure ('#' number slots,
// '\' line-break escapes, and the [NUM]/[RECIPE]/[CHARA]/[GENDER]/[ITEM]
// tokens used by quest-driven text).

var stringsJPPlaceholderTokens = []string{
	"[NUM]", "[RECIPE]", "[CHARA]", "[GENDER]", "[ITEM]", "#", "\\",
}

func ReadStringsJP(file io.Reader) ([]string, error) {
	data, err := io.ReadAll(file)
	if err != nil {
		return nil, err
	}
	if !utf8.Valid(data) {
		return nil, fmt.Errorf("strings.bin.mid: not valid UTF-8")
	}
	if len(data) >= 3 && data[0] == 0xEF && data[1] == 0xBB && data[2] == 0xBF {
		return nil, fmt.Errorf("strings.bin.mid: unexpected UTF-8 BOM")
	}
	return strings.Split(string(data), "\n"), nil
}

func WriteStringsJP(file io.Writer, lines []string) error {
	_, err := io.WriteString(file, strings.Join(lines, "\n"))
	return err
}

// ValidateStringsJPReplacement checks that `updated` is a safe line-for-line
// replacement of `original`. It returns an error describing every violated
// line rather than stopping at the first one.
func ValidateStringsJPReplacement(original, updated []string) error {
	if len(updated) != len(original) {
		return fmt.Errorf("line count changed: %d -> %d; the file is index-addressed and must keep exactly %d lines",
			len(original), len(updated), len(original))
	}

	var problems []string
	for i := range original {
		if !utf8.ValidString(updated[i]) {
			problems = append(problems, fmt.Sprintf("line %d: not valid UTF-8", i))
			continue
		}
		if strings.ContainsRune(updated[i], '\r') {
			problems = append(problems, fmt.Sprintf("line %d: contains carriage return", i))
			continue
		}
		if (original[i] == "") != (updated[i] == "") {
			problems = append(problems, fmt.Sprintf("line %d: empty/non-empty state changed (%q -> %q)",
				i, truncateForError(original[i]), truncateForError(updated[i])))
			continue
		}
		for _, token := range stringsJPPlaceholderTokens {
			if o, u := strings.Count(original[i], token), strings.Count(updated[i], token); o != u {
				problems = append(problems, fmt.Sprintf("line %d: placeholder %q count changed %d -> %d",
					i, token, o, u))
			}
		}
	}

	if len(problems) > 0 {
		return fmt.Errorf("strings replacement rejected (%d problem(s)):\n  %s",
			len(problems), strings.Join(problems, "\n  "))
	}
	return nil
}

// WriteStringsJPReplacement validates `updated` against `original` and only
// writes when validation passes.
func WriteStringsJPReplacement(file io.Writer, original, updated []string) error {
	if err := ValidateStringsJPReplacement(original, updated); err != nil {
		return err
	}
	return WriteStringsJP(file, updated)
}

func truncateForError(s string) string {
	if len(s) > 40 {
		return s[:40] + "…"
	}
	return s
}
