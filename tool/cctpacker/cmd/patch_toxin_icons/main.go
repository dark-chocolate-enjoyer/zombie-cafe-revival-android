package main

import (
	"cctpacker/cct_file"
	"errors"
	"file_types"
	"flag"
	"fmt"
	"image"
	"image/color"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"github.com/disintegration/imaging"
)

type replacement struct {
	index int
	path  string
	image *image.NRGBA
}

func main() {
	atlasIn := flag.String("atlas-in", "", "Input .cct.mid atlas")
	offsetsIn := flag.String("offsets-in", "", "Input offsets file")
	atlasOut := flag.String("atlas-out", "", "Output .cct.mid atlas")
	offsetsOut := flag.String("offsets-out", "", "Output offsets file")
	replacementSpec := flag.String("replace", "", "Comma-separated index=PNG replacements")
	fitExisting := flag.Bool("fit-existing", false, "Resize replacements to their existing atlas rectangles")
	flag.Parse()

	if err := run(*atlasIn, *offsetsIn, *atlasOut, *offsetsOut, *replacementSpec, *fitExisting); err != nil {
		fmt.Fprintln(os.Stderr, "patch_toxin_icons:", err)
		os.Exit(1)
	}
}

func run(atlasIn, offsetsIn, atlasOut, offsetsOut, replacementSpec string, fitExisting bool) error {
	if atlasIn == "" || offsetsIn == "" || atlasOut == "" || offsetsOut == "" || replacementSpec == "" {
		return errors.New("all input, output, and replacement flags are required")
	}
	if atlasIn == atlasOut || offsetsIn == offsetsOut {
		return errors.New("output paths must differ from input paths")
	}

	atlasFile, err := os.Open(atlasIn)
	if err != nil {
		return err
	}
	defer atlasFile.Close()

	offsetsFile, err := os.Open(offsetsIn)
	if err != nil {
		return err
	}
	defer offsetsFile.Close()

	texture, atlas := cct_file.ReadCCTexture(atlasFile)
	offsets := file_types.ReadImageOffsets(offsetsFile)
	replacements, err := readReplacements(replacementSpec, len(offsets.Offsets))
	if err != nil {
		return err
	}

	targets := make(map[int]bool, len(replacements))
	for _, item := range replacements {
		targets[item.index] = true
	}

	if fitExisting {
		for _, item := range replacements {
			entry := offsets.Offsets[item.index]
			width := int(entry.W)
			height := int(entry.H)
			fitted := imaging.Resize(item.image, width, height, imaging.Lanczos)
			clear(atlas, int(entry.X), int(entry.Y), width, height)
			atlas = imaging.Paste(atlas, fitted, image.Pt(int(entry.X), int(entry.Y)))
			fmt.Printf("index %d -> existing (%d,%d) %dx%d from %s\n",
				item.index, entry.X, entry.Y, width, height, item.path)
		}
	} else {
		occupied := make([]bool, int(texture.Width*texture.Height))
		mark := func(x, y, width, height int) {
			for py := maxInt(0, y); py < minInt(int(texture.Height), y+height); py++ {
				for px := maxInt(0, x); px < minInt(int(texture.Width), x+width); px++ {
					occupied[py*int(texture.Width)+px] = true
				}
			}
		}

		for index, entry := range offsets.Offsets {
			if targets[index] {
				clear(atlas, int(entry.X), int(entry.Y), int(entry.W), int(entry.H))
				continue
			}
			mark(int(entry.X), int(entry.Y), int(entry.W), int(entry.H))
		}

		sort.Slice(replacements, func(i, j int) bool {
			left := replacements[i].image.Bounds().Dx() * replacements[i].image.Bounds().Dy()
			right := replacements[j].image.Bounds().Dx() * replacements[j].image.Bounds().Dy()
			return left > right
		})

		for _, item := range replacements {
			width := item.image.Bounds().Dx()
			height := item.image.Bounds().Dy()
			x, y, ok := findSpace(occupied, int(texture.Width), int(texture.Height), width, height)
			if !ok {
				return fmt.Errorf("no free %dx%d rectangle for index %d", width, height, item.index)
			}

			atlas = imaging.Paste(atlas, item.image, image.Pt(x, y))
			mark(x, y, width, height)

			entry := &offsets.Offsets[item.index]
			entry.X = int16(x)
			entry.Y = int16(y)
			entry.W = int16(width)
			entry.H = int16(height)
			fmt.Printf("index %d -> (%d,%d) %dx%d from %s\n", item.index, x, y, width, height, item.path)
		}
	}

	if err := os.MkdirAll(filepath.Dir(atlasOut), 0o755); err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(offsetsOut), 0o755); err != nil {
		return err
	}

	atlasTemp := atlasOut + ".tmp"
	offsetsTemp := offsetsOut + ".tmp"
	atlasOutput, err := os.Create(atlasTemp)
	if err != nil {
		return err
	}
	cct_file.WriteCCTexture(atlasOutput, texture, atlas)
	if err := atlasOutput.Close(); err != nil {
		return err
	}

	offsetsOutput, err := os.Create(offsetsTemp)
	if err != nil {
		return err
	}
	file_types.WriteImageOffsets(offsetsOutput, offsets)
	if err := offsetsOutput.Close(); err != nil {
		return err
	}

	if err := os.Rename(atlasTemp, atlasOut); err != nil {
		return err
	}
	if err := os.Rename(offsetsTemp, offsetsOut); err != nil {
		return err
	}
	return nil
}

func readReplacements(spec string, offsetCount int) ([]replacement, error) {
	var result []replacement
	seen := map[int]bool{}
	for _, pair := range strings.Split(spec, ",") {
		parts := strings.SplitN(pair, "=", 2)
		if len(parts) != 2 {
			return nil, fmt.Errorf("invalid replacement %q", pair)
		}
		index, err := strconv.Atoi(parts[0])
		if err != nil || index < 0 || index >= offsetCount {
			return nil, fmt.Errorf("invalid replacement index %q", parts[0])
		}
		if seen[index] {
			return nil, fmt.Errorf("duplicate replacement index %d", index)
		}
		seen[index] = true

		decoded, err := imaging.Open(parts[1])
		if err != nil {
			return nil, err
		}
		nrgba, ok := decoded.(*image.NRGBA)
		if !ok {
			nrgba = imaging.Clone(decoded)
		}
		result = append(result, replacement{index: index, path: parts[1], image: nrgba})
	}
	return result, nil
}

func findSpace(occupied []bool, atlasWidth, atlasHeight, width, height int) (int, int, bool) {
	const padding = 1
	for y := padding; y+height+padding <= atlasHeight; y++ {
		for x := padding; x+width+padding <= atlasWidth; x++ {
			if rectangleFree(occupied, atlasWidth, x-padding, y-padding, width+padding*2, height+padding*2) {
				return x, y, true
			}
		}
	}
	return 0, 0, false
}

func rectangleFree(occupied []bool, atlasWidth, x, y, width, height int) bool {
	for py := y; py < y+height; py++ {
		row := py * atlasWidth
		for px := x; px < x+width; px++ {
			if occupied[row+px] {
				return false
			}
		}
	}
	return true
}

func clear(atlas *image.NRGBA, x, y, width, height int) {
	transparent := color.NRGBA{}
	for py := y; py < y+height; py++ {
		for px := x; px < x+width; px++ {
			atlas.SetNRGBA(px, py, transparent)
		}
	}
}

func minInt(left, right int) int {
	if left < right {
		return left
	}
	return right
}

func maxInt(left, right int) int {
	if left > right {
		return left
	}
	return right
}
