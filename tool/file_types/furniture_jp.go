package file_types

import (
	"io"
)

// FurnitureJP is the JP 1.7.0 furnitureData.bin.mid record. Relative to the
// EN Furniture record it inserts UMid (int32, zero in 827/835 records; the
// nonzero values decompose into two int16s) before RatingBonus, and replaces
// the EN U21/U22/U23 tail with a float32/int16/float32 triple whose values
// look like event multipliers (1.0/1.5/2.0). Image indices refer into the
// offsets file selected by ImagePackIndex and are NOT compatible with EN
// indices.
type FurnitureJP struct {
	UnlockLevel        byte
	Name               string
	Price              int32
	PurchaseWithToxin  bool
	SizeX              byte
	SizeY              byte
	ImageIndexNorth    int16
	ImageIndexEast     int16
	ImageIndexSouth    int16
	ImageIndexWest     int16
	Type               byte
	Category           byte
	Color              []int
	MoneyPerHour       int16
	MaximumMoney       int16
	UMid               int32
	RatingBonus        float32
	BuyMoneyAmount     int32
	ImagePackIndex     byte
	StoveSpeedMult     float32
	Description        string
	ExperiencePoints   float32
	IsAvailableInStore bool
	UTailFloat1        float32
	UTailInt           int16
	UTailFloat2        float32
}

func readSingleFurnitureJP(file io.Reader) FurnitureJP {
	var furniture FurnitureJP

	furniture.UnlockLevel = ReadByte(file)
	furniture.Name = ReadString(file)
	furniture.Price = ReadInt32(file)
	furniture.PurchaseWithToxin = ReadBool(file)
	furniture.SizeX = ReadByte(file)
	furniture.SizeY = ReadByte(file)
	furniture.ImageIndexNorth = ReadInt16(file)
	furniture.ImageIndexEast = ReadInt16(file)
	furniture.ImageIndexSouth = ReadInt16(file)
	furniture.ImageIndexWest = ReadInt16(file)
	furniture.Type = ReadByte(file)
	furniture.Category = ReadByte(file)

	colorBytes := ReadNextBytes(file, 4)
	colorInts := make([]int, len(colorBytes))
	for i, b := range colorBytes {
		colorInts[i] = int(b)
	}
	furniture.Color = colorInts

	furniture.MoneyPerHour = ReadInt16(file)
	furniture.MaximumMoney = ReadInt16(file)
	furniture.UMid = ReadInt32(file)
	furniture.RatingBonus = ReadFloat(file)
	furniture.BuyMoneyAmount = ReadInt32(file)
	furniture.ImagePackIndex = ReadByte(file)
	furniture.StoveSpeedMult = ReadFloat(file)
	furniture.Description = ReadString(file)
	furniture.ExperiencePoints = ReadFloat(file)
	furniture.IsAvailableInStore = ReadBool(file)
	furniture.UTailFloat1 = ReadFloat(file)
	furniture.UTailInt = ReadInt16(file)
	furniture.UTailFloat2 = ReadFloat(file)

	return furniture
}

func writeSingleFurnitureJP(file io.Writer, data FurnitureJP) {
	WriteByte(file, data.UnlockLevel)
	WriteString(file, data.Name)
	WriteInt32(file, data.Price)
	WriteBool(file, data.PurchaseWithToxin)
	WriteByte(file, data.SizeX)
	WriteByte(file, data.SizeY)
	WriteInt16(file, data.ImageIndexNorth)
	WriteInt16(file, data.ImageIndexEast)
	WriteInt16(file, data.ImageIndexSouth)
	WriteInt16(file, data.ImageIndexWest)
	WriteByte(file, data.Type)
	WriteByte(file, data.Category)

	for _, b := range data.Color {
		WriteByte(file, byte(b))
	}

	WriteInt16(file, data.MoneyPerHour)
	WriteInt16(file, data.MaximumMoney)
	WriteInt32(file, data.UMid)
	WriteFloat(file, data.RatingBonus)
	WriteInt32(file, data.BuyMoneyAmount)
	WriteByte(file, data.ImagePackIndex)
	WriteFloat(file, data.StoveSpeedMult)
	WriteString(file, data.Description)
	WriteFloat(file, data.ExperiencePoints)
	WriteBool(file, data.IsAvailableInStore)
	WriteFloat(file, data.UTailFloat1)
	WriteInt16(file, data.UTailInt)
	WriteFloat(file, data.UTailFloat2)
}

func ReadFurnitureDataJP(file io.Reader) []FurnitureJP {
	num := int(ReadInt32(file))
	data := []FurnitureJP{}

	for i := 0; i < num; i++ {
		data = append(data, readSingleFurnitureJP(file))
	}

	return data
}

func WriteFurnitureDataJP(file io.Writer, furnitures []FurnitureJP) {
	WriteInt32(file, int32(len(furnitures)))

	for i := 0; i < len(furnitures); i++ {
		writeSingleFurnitureJP(file, furnitures[i])
	}
}
