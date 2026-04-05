from __future__ import annotations


diag_touch_grid = [
    [1, 0],
    [0, 1],
]

single_object_translate_right = {
    "input": [[2, 0, 0], [2, 0, 0], [0, 0, 0]],
    "output": [[0, 2, 0], [0, 2, 0], [0, 0, 0]],
}

copy_then_translate_by_width = {
    "input": [[3, 0, 3]],
    "output": [[3, 0, 3, 3, 0, 3]],
}

single_object_recolor = {
    "input": [[1, 1], [0, 0]],
    "output": [[2, 2], [0, 0]],
}

single_object_delete = {
    "input": [[4, 4], [4, 4]],
    "output": [[0, 0], [0, 0]],
}

rotate_rect_object = {
    "input": [[5, 5, 0], [5, 0, 0]],
    "output": [[5, 5], [0, 5], [0, 0]],
}

flip_rect_object = {
    "input": [[6, 0, 0], [6, 6, 0]],
    "output": [[0, 0, 6], [0, 6, 6]],
}

fill_center_hole = {
    "input": [[7, 7, 7], [7, 0, 7], [7, 7, 7]],
    "output": [[7, 7, 7], [7, 7, 7], [7, 7, 7]],
}

crop_center_cell = {
    "input": [[0, 0, 0], [0, 8, 0], [0, 0, 0]],
    "output": [[8]],
}

crop_center_bbox = {
    "input": [[0, 0, 0, 0], [0, 9, 9, 0], [0, 9, 9, 0], [0, 0, 0, 0]],
    "output": [[9, 9], [9, 9]],
}
