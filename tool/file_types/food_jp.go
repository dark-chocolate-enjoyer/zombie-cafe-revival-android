package file_types

import (
	"io"
)

// FoodJP is the JP 1.7.0 foodData.bin.mid record. It is shorter than the EN
// Food record: the EN trailing U9/U10/U11/U12 fields do not exist in the JP
// file. ImageID is unique across all 234 JP records and matches the EN
// ImageID for dishes shared between the builds.
type FoodJP struct {
	Name             string
	Price            int16
	UnlockLevel      byte
	CookTimeMinutes  int16
	Servings         int16
	PricePerServing  int16
	ExperiencePoints int16
	ImageID          int16
	U7               byte
	U8               byte
}

func readSingleFoodJP(file io.Reader) FoodJP {
	var food FoodJP
	food.Name = ReadString(file)
	food.Price = ReadInt16(file)
	food.UnlockLevel = ReadByte(file)
	food.CookTimeMinutes = ReadInt16(file)
	food.Servings = ReadInt16(file)
	food.PricePerServing = ReadInt16(file)
	food.ExperiencePoints = ReadInt16(file)
	food.ImageID = ReadInt16(file)
	food.U7 = ReadByte(file)
	food.U8 = ReadByte(file)
	return food
}

func writeSingleFoodJP(file io.Writer, data FoodJP) {
	WriteString(file, data.Name)
	WriteInt16(file, data.Price)
	WriteByte(file, data.UnlockLevel)
	WriteInt16(file, data.CookTimeMinutes)
	WriteInt16(file, data.Servings)
	WriteInt16(file, data.PricePerServing)
	WriteInt16(file, data.ExperiencePoints)
	WriteInt16(file, data.ImageID)
	WriteByte(file, data.U7)
	WriteByte(file, data.U8)
}

func ReadFoodsJP(file io.Reader) []FoodJP {
	num := int(ReadByte(file))
	data := []FoodJP{}

	for i := 0; i < num; i++ {
		data = append(data, readSingleFoodJP(file))
	}

	return data
}

func WriteFoodsJP(file io.Writer, foods []FoodJP) {
	WriteByte(file, byte(len(foods)))

	for i := 0; i < len(foods); i++ {
		writeSingleFoodJP(file, foods[i])
	}
}
