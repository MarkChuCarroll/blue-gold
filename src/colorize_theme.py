"""
 * Copyright 2024 Mark C. Chu-Carroll
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.

This is ridiculously overdone, but I had fun doing it.

The problem that this solves is:  there are a _lot_ of colors in a VScode theme.
And the way that you write them in a theme file, it's a whole lot of 6-digit
hexidecimal RGB codes. For a good looking theme, you want to re-use a lot
of those, but it's really hard to remember which random six digit string
is which. (I mean, yeah, you can remember that, say, "#435acd" is going to be
a shade of blue,  but are you going to remember which of #7a94df and #626388 is the slate
gray that you're using for window borders?)

So I wanted to have a way of using color names.

And then I added another layer: since I know that I want to
be reusing colors for similar UI elements, I created a mapping from
a common UI element to a color name. That way, if I decide I want all
of the borders to be green instead of blue, I can just change one
line.
"""

from typing import *
import json
import sys
from argparse import ArgumentParser


Color: TypeAlias = str
ColorName: TypeAlias = str
ColorGroup: TypeAlias = Dict[ColorName, Color]
ColorMap: TypeAlias = Dict[str, ColorGroup]
ElementName: TypeAlias = str
ElementColorBindings = Dict[ElementName, ColorName]
ColorBinding = Dict[str, ElementColorBindings]


class ColorMappings:
    """
    Manage the two-stage mapping for color assignments.

    The first level is just naming colors. To keep it organized, the colors are  grouped
    into categories. Each category is just a map from color name to RGB value. You can
    refer to a color with just its name if it's unique, or with its category
    qualifier.

    The second level is semantic entities in the interface. So you can say, for
    example, that all text in the UI should have a blue backround by setting "ui_elements.text_bg"
    to "blue".
    """
    @classmethod
    def load(cls, fp: TextIO):
        mappings = json.load(fp)
        return ColorMappings(mappings["color_groups"], mappings["binding_groups"])

    def __init__(self, colors: ColorMap, bindings: ElementColorBindings):
        self.color_map: ColorMap = colors
        self.all_colors: Dict[str, str] = {}
        for gr in self.color_map.values():
            for (name, value) in gr.items():
                if name not in self.all_colors:
                    self.all_colors[name] = value
        self.bindings: ElementColorBindings = bindings

    def _decompose_name(self, name: str) -> Tuple[str | None, str]:
        if "." not in name:
            return (None, name)
        else:
            if name.count(".") > 1:
                raise Exception(
                    f"A qualified name can only have one '.' ({name})")
            return name.split(".")

    def get_color_for_name(self, color: str) -> str:
        qual, name = self._decompose_name(color)
        if qual is None:
            if name not in self.all_colors:
                raise Exception(f"Color {name} not found")
            else:
                return self.all_colors[name]
        else:
            if qual not in self.color_map:
                raise Exception(f"Color group {qual} not found")
            gr = self.color_map[qual]
            if name not in gr:
                raise Exception(f"Color {name} not in group {qual}")
            return gr[name]

    def get_color_name_for_binding(self, binding_name: str) -> str:
        qual, name = self._decompose_name(binding_name)
        if qual is None:
            raise Exception(
                f"Binding names must be qualified ({binding_name})")
        if qual not in self.bindings:
            raise Exception(f"Binding category {qual} not found")
        cat = self.bindings[qual]
        if name not in cat:
            raise Exception(f"Color {name} not found in category {qual}")
        return cat[name]

    def get_color_for_binding(self, binding_name: str) -> str:
        return self.get_color_for_name(self.get_color_name_for_binding(binding_name))

    def apply_to_theme(self, themeFile):
        with open(themeFile, "r") as i:
            theme = json.load(i)
        for themeColor in theme["colors"]:
            element_color = theme["colors"][themeColor]
            if not element_color.startswith("#"):
                theme["colors"][themeColor] = self.get_color_for_binding(
                    element_color)
        token_colors = theme["tokenColors"]
        for obj in token_colors:
            if "settings" in obj:
                settings = obj["settings"]
                if "foreground" in settings:
                    fg = settings["foreground"]
                    if not fg.startswith("#"):
                        settings["foreground"] = self.get_color_for_binding(fg)
                if "background" in settings:
                    bg = settings["background"]
                    if not bg.startswith("#"):
                        settings["background"] = self.get_color_for_binding(bg)
        return theme


def main():
    arg_parser = ArgumentParser("VSCode Theme Color Binder")
    arg_parser.add_argument("--colors", type=str,
                            help="The file containing the colormaps", required=True)
    arg_parser.add_argument(
        "--input", type=str, help="The template file to transform", required=True)
    arg_parser.add_argument(
        "--output", type=str, help="The theme file to write output to", required=False)
    args = arg_parser.parse_args()

    with open(args.colors, "r") as i:
        color_map = ColorMappings.load(i)
    try:
        theme = color_map.apply_to_theme(args.input)
        if args.output is None:
            print(json.dumps(theme, indent=2, separators=(",", ":")))
        else:
            with open(args.output, "w") as out:
                json.dump(theme, indent=2, separators=(",", ":"), fp=out)

    except Exception as e:
        print(f"Error: {e}")
        raise e


if __name__ == "__main__":
    main()
