package file_types

import (
	"io"
)

// Enemy/colosseum café content files, decoded in pass 4
// (jp/research/pass4_systems_curation/enemy_colosseum_schema_report.md).
// All three formats are shared between the EN revival and JP 1.7.0 builds
// and validate to exact EOF on every shipped file.

// ItemSet is one record of enemyItems.bin.mid / colosseumItems.bin.mid:
// a café name plus 16 slot strings, each an underscore-joined list of
// furnitureData row indices (e.g. "4_23_24_25_26_42"); slots may be empty.
// The 16-slot width is constant across all 195 shipped records (180 JP
// enemyItems + 14 EN enemyItems + 1 JP colosseumItems); it is asserted by
// the round-trip tests rather than inferred per record.
type ItemSet struct {
	Name  string
	Slots [16]string
}

func readSingleItemSet(file io.Reader) ItemSet {
	var set ItemSet
	set.Name = ReadString(file)
	for i := range set.Slots {
		set.Slots[i] = ReadString(file)
	}
	return set
}

func writeSingleItemSet(file io.Writer, data ItemSet) {
	WriteString(file, data.Name)
	for i := range data.Slots {
		WriteString(file, data.Slots[i])
	}
}

func ReadItemSets(file io.Reader) []ItemSet {
	num := int(ReadInt16(file))
	data := []ItemSet{}

	for i := 0; i < num; i++ {
		data = append(data, readSingleItemSet(file))
	}

	return data
}

func WriteItemSets(file io.Writer, sets []ItemSet) {
	WriteInt16(file, int16(len(sets)))

	for i := 0; i < len(sets); i++ {
		writeSingleItemSet(file, sets[i])
	}
}

// PlacementRecord is one record of enemyLayouts.bin.mid /
// colosseumLayouts.bin.mid. Records with an empty Type are group headers:
// (A, B, C) = (placement count, width, height) of the layout that the next
// A records belong to. For placement records Type is a one-letter item-slot
// code (H/T/W/L/A/S/C/G/F/P/B/I/D/E observed); the meaning of A/B/C
// (position/rotation/variant) is not yet established, so they are kept as
// raw values.
type PlacementRecord struct {
	Type string
	A    int32
	B    int32
	C    int32
}

func readSinglePlacement(file io.Reader) PlacementRecord {
	var rec PlacementRecord
	rec.Type = ReadString(file)
	rec.A = ReadInt32(file)
	rec.B = ReadInt32(file)
	rec.C = ReadInt32(file)
	return rec
}

func writeSinglePlacement(file io.Writer, data PlacementRecord) {
	WriteString(file, data.Type)
	WriteInt32(file, data.A)
	WriteInt32(file, data.B)
	WriteInt32(file, data.C)
}

func ReadPlacementLayouts(file io.Reader) []PlacementRecord {
	num := int(ReadInt16(file))
	data := []PlacementRecord{}

	for i := 0; i < num; i++ {
		data = append(data, readSinglePlacement(file))
	}

	return data
}

func WritePlacementLayouts(file io.Writer, records []PlacementRecord) {
	WriteInt16(file, int16(len(records)))

	for i := 0; i < len(records); i++ {
		writeSinglePlacement(file, records[i])
	}
}

// EnemyItemDataRow is one row of enemyItemData.bin.mid: a u8-count-prefixed
// matrix of 16 small values per row (byte-identical between the EN and JP
// builds). Row/column semantics are open; values are kept raw.
type EnemyItemDataRow [16]byte

func ReadEnemyItemData(file io.Reader) []EnemyItemDataRow {
	num := int(ReadByte(file))
	data := []EnemyItemDataRow{}

	for i := 0; i < num; i++ {
		var row EnemyItemDataRow
		copy(row[:], ReadNextBytes(file, 16))
		data = append(data, row)
	}

	return data
}

func WriteEnemyItemData(file io.Writer, rows []EnemyItemDataRow) {
	WriteByte(file, byte(len(rows)))

	for i := 0; i < len(rows); i++ {
		file.Write(rows[i][:])
	}
}
