package file_types

import (
	"io"
)

// CharacterJP is the JP 1.7.0 characterData.bin.mid record. The record count
// is an int16 (EN uses a byte) and the stat fields are wider than EN
// (Energy int32, Speed/Attack/TipRating int16). Category corresponds to the
// EN CharacterArtStringHead field.
type CharacterJP struct {
	CafeLevelRequired  byte
	U2                 byte
	U3                 byte
	Name               string
	Category           string
	CharacterArtString string
	U4                 byte
	Energy             int32
	Speed              int16
	AttackStrength     int16
	TipRating          int16
	U9                 int16
	U10                int16
	U11                int16
	U12                int16
	IsFemale           bool
	Cost               int32
	// PurchaseWithToxin is a bool in the EN schema, but must stay a raw byte
	// here: JP record 148 carries the out-of-range value 10.
	PurchaseWithToxin byte
	PlayableFlag      byte
	CookSpeedBonus    float32
	TipMultiplier     int32
	U19               float32
	U20               float32
	U21               byte
	U22               int16
	U23               float32
	HumanDescription  string
	ZombieDescription string
}

func readSingleCharacterJP(file io.Reader) CharacterJP {
	var c CharacterJP

	c.CafeLevelRequired = ReadByte(file)
	c.U2 = ReadByte(file)
	c.U3 = ReadByte(file)

	c.Name = ReadString(file)
	c.Category = ReadString(file)
	c.CharacterArtString = ReadString(file)

	c.U4 = ReadByte(file)

	c.Energy = ReadInt32(file)

	c.Speed = ReadInt16(file)
	c.AttackStrength = ReadInt16(file)

	c.TipRating = ReadInt16(file)
	c.U9 = ReadInt16(file)
	c.U10 = ReadInt16(file)
	c.U11 = ReadInt16(file)

	c.U12 = ReadInt16(file)

	c.IsFemale = ReadBool(file)

	c.Cost = ReadInt32(file)

	c.PurchaseWithToxin = ReadByte(file)
	c.PlayableFlag = ReadByte(file)

	c.CookSpeedBonus = ReadFloat(file)
	c.TipMultiplier = ReadInt32(file)

	c.U19 = ReadFloat(file)
	c.U20 = ReadFloat(file)

	c.U21 = ReadByte(file)
	c.U22 = ReadInt16(file)
	c.U23 = ReadFloat(file)

	c.HumanDescription = ReadString(file)
	c.ZombieDescription = ReadString(file)

	return c
}

func writeSingleCharacterJP(file io.Writer, c CharacterJP) {
	WriteByte(file, c.CafeLevelRequired)
	WriteByte(file, c.U2)
	WriteByte(file, c.U3)

	WriteString(file, c.Name)
	WriteString(file, c.Category)
	WriteString(file, c.CharacterArtString)

	WriteByte(file, c.U4)

	WriteInt32(file, c.Energy)

	WriteInt16(file, c.Speed)
	WriteInt16(file, c.AttackStrength)

	WriteInt16(file, c.TipRating)
	WriteInt16(file, c.U9)
	WriteInt16(file, c.U10)
	WriteInt16(file, c.U11)

	WriteInt16(file, c.U12)

	WriteBool(file, c.IsFemale)

	WriteInt32(file, c.Cost)

	WriteByte(file, c.PurchaseWithToxin)
	WriteByte(file, c.PlayableFlag)

	WriteFloat(file, c.CookSpeedBonus)
	WriteInt32(file, c.TipMultiplier)

	WriteFloat(file, c.U19)
	WriteFloat(file, c.U20)

	WriteByte(file, c.U21)
	WriteInt16(file, c.U22)
	WriteFloat(file, c.U23)

	WriteString(file, c.HumanDescription)
	WriteString(file, c.ZombieDescription)
}

func ReadCharactersJP(file io.Reader) []CharacterJP {
	data := []CharacterJP{}
	n := ReadInt16(file)
	for i := 0; i < int(n); i++ {
		data = append(data, readSingleCharacterJP(file))
	}
	return data
}

func WriteCharactersJP(file io.Writer, characters []CharacterJP) {
	WriteInt16(file, int16(len(characters)))
	for i := 0; i < len(characters); i++ {
		writeSingleCharacterJP(file, characters[i])
	}
}
