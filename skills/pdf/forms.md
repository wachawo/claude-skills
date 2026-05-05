**CRITICAL: You MUST follow these steps in order. Do not jump straight to writing code.**

If you need to fill a PDF form, first check whether the PDF contains interactive form fields. Run this script from this file's directory:
 `python scripts/check_fillable_fields <file.pdf>`, and depending on the result go either to the "Fillable fields" section or the "Non-fillable fields" section and follow the matching instructions.

# Fillable fields
If the PDF contains interactive form fields:
- Run this script from this file's directory: `python scripts/extract_form_field_info.py <input.pdf> <field_info.json>`. It creates a JSON file listing the fields in this format:
```
[
  {
    "field_id": (unique ID for the field),
    "page": (page number, 1-based),
    "rect": ([left, bottom, right, top] bounding box in PDF coordinates, y=0 is the bottom of the page),
    "type": ("text", "checkbox", "radio_group", or "choice"),
  },
  // Checkboxes have "checked_value" and "unchecked_value" properties:
  {
    "field_id": (unique ID for the field),
    "page": (page number, 1-based),
    "type": "checkbox",
    "checked_value": (Set the field to this value to check the checkbox),
    "unchecked_value": (Set the field to this value to uncheck the checkbox),
  },
  // Radio groups have a "radio_options" list with the possible choices.
  {
    "field_id": (unique ID for the field),
    "page": (page number, 1-based),
    "type": "radio_group",
    "radio_options": [
      {
        "value": (set the field to this value to select this radio option),
        "rect": (bounding box for the radio button for this option)
      },
      // Other radio options
    ]
  },
  // Multiple choice fields have a "choice_options" list with the possible choices:
  {
    "field_id": (unique ID for the field),
    "page": (page number, 1-based),
    "type": "choice",
    "choice_options": [
      {
        "value": (set the field to this value to select this option),
        "text": (display text of the option)
      },
      // Other choice options
    ],
  }
]
```
- Convert the PDF to PNGs (one image per page) with this script (run from this file's directory):
`python scripts/convert_pdf_to_images.py <file.pdf> <output_directory>`
Then analyze the images to determine the purpose of each form field (be sure to convert bounding-box coordinates from PDF to image coordinates).
- Create a `field_values.json` file in this format with the values to fill into each field:
```
[
  {
    "field_id": "last_name", // Must match the field_id from `extract_form_field_info.py`
    "description": "The user's last name",
    "page": 1, // Must match the "page" value in field_info.json
    "value": "Simpson"
  },
  {
    "field_id": "Checkbox12",
    "description": "Checkbox to be checked if the user is 18 or over",
    "page": 1,
    "value": "/On" // If this is a checkbox, use its "checked_value" value to check it. If it's a radio button group, use one of the "value" values in "radio_options".
  },
  // more fields
]
```
- Run the `fill_fillable_fields.py` script from this file's directory to produce a filled PDF:
`python scripts/fill_fillable_fields.py <input pdf> <field_values.json> <output pdf>`
This script verifies that the field IDs and values you provided are valid; if it prints errors, fix the affected fields and try again.

# Non-fillable fields
If the PDF has no interactive form fields, add text annotations. First try to extract coordinates from the PDF structure (more accurate), and fall back to visual estimation when needed.

## Step 1: Try structure extraction first

Run this script to extract text labels, lines, and checkboxes with their precise PDF coordinates:
`python scripts/extract_form_structure.py <input.pdf> form_structure.json`

This produces a JSON file containing:
- **labels**: each text element with precise coordinates (x0, top, x1, bottom in PDF points)
- **lines**: horizontal lines defining row boundaries
- **checkboxes**: small square rectangles that are checkboxes (with center coordinates)
- **row_boundaries**: row top/bottom positions computed from the horizontal lines

**Check the results**: If `form_structure.json` contains meaningful labels (text elements that match form fields), use **Approach A: structure-based coordinates**. If the PDF is scanned/image-based and contains few or no labels, use **Approach B: visual estimation**.

---

## Approach A: structure-based coordinates (preferred)

Use this when `extract_form_structure.py` found text labels in the PDF.

### A.1: Analyze the structure

Read form_structure.json and identify:

1. **Label groups**: adjacent text elements that form a single label (e.g. "Last" + "Name")
2. **Row structure**: labels with similar `top` values are in the same row
3. **Field columns**: entry areas start after the end of the label (x0 = label.x1 + gap)
4. **Checkboxes**: use the checkbox coordinates directly from the structure

**Coordinate system**: PDF coordinates with y=0 at the TOP of the page, y increasing downward.

### A.2: Check for missing elements

Structure extraction may miss some form elements. Common cases:
- **Round checkboxes**: only square rectangles are recognized as checkboxes
- **Complex graphics**: decorative elements or non-standard form controls
- **Faint or light elements**: may not be extracted

If you see form fields in the PDF images that don't appear in form_structure.json, those specific fields require **visual analysis** (see "Hybrid approach" below).

### A.3: Build fields.json with PDF coordinates

For each field, compute entry coordinates from the extracted structure:

**Text fields:**
- entry x0 = label x1 + 5 (small gap after the label)
- entry x1 = x0 of the next label or the row boundary
- entry top = same as label top
- entry bottom = the row boundary below or label bottom + row_height

**Checkboxes:**
- Use the checkbox rectangle coordinates directly from form_structure.json
- entry_bounding_box = [checkbox.x0, checkbox.top, checkbox.x1, checkbox.bottom]

Build fields.json using `pdf_width` and `pdf_height` (this signals PDF coordinates):
```json
{
  "pages": [
    {"page_number": 1, "pdf_width": 612, "pdf_height": 792}
  ],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Last name entry field",
      "field_label": "Last Name",
      "label_bounding_box": [43, 63, 87, 73],
      "entry_bounding_box": [92, 63, 260, 79],
      "entry_text": {"text": "Smith", "font_size": 10}
    },
    {
      "page_number": 1,
      "description": "US Citizen Yes checkbox",
      "field_label": "Yes",
      "label_bounding_box": [260, 200, 280, 210],
      "entry_bounding_box": [285, 197, 292, 205],
      "entry_text": {"text": "X"}
    }
  ]
}
```

**Important**: use `pdf_width`/`pdf_height` and coordinates straight from form_structure.json.

### A.4: Validate bounding boxes

Before filling, validate the bounding boxes for errors:
`python scripts/check_bounding_boxes.py fields.json`

This checks for overlapping rectangles and entry fields that are too small for the specified font size. Fix any reported errors before filling.

---

## Approach B: visual estimation (fallback)

Use this when the PDF is scanned/image-based and structure extraction did not find usable text labels (e.g. all text shows up as `(cid:X)` patterns).

### B.1: Convert the PDF to images

`python scripts/convert_pdf_to_images.py <input.pdf> <images_dir/>`

### B.2: Initial field identification

Examine each page image to outline form sections and obtain **rough estimates** of field placement:
- Form field labels and their approximate positions
- Entry areas (lines, rectangles, or empty spaces for entering text)
- Checkboxes and their approximate positions

For each field, record approximate pixel coordinates (precision is not yet required).

### B.3: Refine with zooming (CRITICAL for accuracy)

For each field, crop the area around the estimated position to refine the coordinates precisely.

**Create a zoomed-in crop with ImageMagick:**
```bash
magick <page_image> -crop <width>x<height>+<x>+<y> +repage <crop_output.png>
```

Where:
- `<x>, <y>` = top-left corner of the crop area (use the rough estimate minus padding)
- `<width>, <height>` = size of the crop area (the field area plus ~50px padding on each side)

**Example:** to refine a "Name" field estimated near (100, 150):
```bash
magick images_dir/page_1.png -crop 300x80+50+120 +repage crops/name_field.png
```

(Note: if the `magick` command is not available, try `convert` with the same arguments.)

**Examine the cropped image** to determine exact coordinates:
1. Identify the exact pixel where the entry area starts (after the label)
2. Identify where the entry area ends (before the next field or the edge)
3. Identify the top and bottom of the entry line/rectangle

**Convert crop coordinates back to full-image coordinates:**
- full_x = crop_x + crop_offset_x
- full_y = crop_y + crop_offset_y

Example: if the crop started at (50, 120) and inside the crop the entry rectangle starts at (52, 18):
- entry_x0 = 52 + 50 = 102
- entry_top = 18 + 120 = 138

**Repeat for each field**, grouping adjacent fields into a single crop where possible.

### B.4: Build fields.json with refined coordinates

Build fields.json using `image_width` and `image_height` (this signals image coordinates):
```json
{
  "pages": [
    {"page_number": 1, "image_width": 1700, "image_height": 2200}
  ],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Last name entry field",
      "field_label": "Last Name",
      "label_bounding_box": [120, 175, 242, 198],
      "entry_bounding_box": [255, 175, 720, 218],
      "entry_text": {"text": "Smith", "font_size": 10}
    }
  ]
}
```

**Important**: use `image_width`/`image_height` and the refined pixel coordinates from the zoom analysis.

### B.5: Validate bounding boxes

Before filling, validate the bounding boxes for errors:
`python scripts/check_bounding_boxes.py fields.json`

This checks for overlapping rectangles and entry fields that are too small for the specified font size. Fix any reported errors before filling.

---

## Hybrid approach: structure + visual

Use this when structure extraction works for most fields but misses some elements (e.g. round checkboxes, non-standard controls).

1. **Use Approach A** for fields found in form_structure.json
2. **Convert the PDF to images** for visual analysis of the missing fields
3. **Use zoom refinement** (from Approach B) for the missing fields
4. **Combine coordinates**: for fields from structure extraction, use `pdf_width`/`pdf_height`. For visually-estimated fields, convert image coordinates to PDF coordinates:
   - pdf_x = image_x * (pdf_width / image_width)
   - pdf_y = image_y * (pdf_height / image_height)
5. **Use a single coordinate system** in fields.json — bring everything into PDF coordinates with `pdf_width`/`pdf_height`

---

## Step 2: Validate before filling

**Always validate the bounding boxes before filling:**
`python scripts/check_bounding_boxes.py fields.json`

Checks for:
- Overlapping bounding boxes (which causes overlapping text)
- Entry fields too small for the specified font size

Fix any reported errors in fields.json before continuing.

## Step 3: Fill the form

The fill script auto-detects the coordinate system and performs the conversion:
`python scripts/fill_pdf_form_with_annotations.py <input.pdf> fields.json <output.pdf>`

## Step 4: Verify the result

Convert the filled PDF to images and check the text placement:
`python scripts/convert_pdf_to_images.py <output.pdf> <verify_images/>`

If text is positioned incorrectly:
- **Approach A**: confirm you are using PDF coordinates from form_structure.json with `pdf_width`/`pdf_height`
- **Approach B**: confirm image dimensions match and coordinates are exact pixels
- **Hybrid**: confirm the coordinate conversions are correct for visually-estimated fields
