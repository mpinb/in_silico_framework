# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Read and write :ref:`hoc_file_format` morphologies.
"""
from __future__ import annotations
from ._edge import _Edge
from typing import List, Optional, Dict, Any
from data_base.dbopen import dbopen
from config.user.morphology import HOC_LABEL_MAP
from config.isf_logging import get_isf_logger
import re

logger = get_isf_logger().getChild(__name__)

def _extract_label_and_name_from_hoc(
    hoc_label,
    remap_labels=None
    ):
    remap_labels = remap_labels or {}
    remap_labels = {k.lower(): v for k, v in remap_labels.items()}
    # Derive the base label: everything before the first '_' or digit
    hoc_name_match = re.match(r'([A-Za-z\d]+)(_.*)', hoc_label)  # match letters and numbers, NOT underscores
    if hoc_name_match:
        label = hoc_name_match.group(1)
        hoc_suffix = hoc_name_match.group(2)
    else:
        label = hoc_label
        hoc_suffix = None

    matched_key = label.lower() if label.lower() in remap_labels else None

    if matched_key is None:
        # check if any map key appears anywhere in the full hoc label
        nonprefix_matches = [k for k in remap_labels if k in hoc_label.lower()]
        if len(nonprefix_matches) > 1:
            raise ValueError(
                f"Ambiguous label '{hoc_label}': multiple map keys match (non-perfix match) as: {nonprefix_matches}"
            )
        if nonprefix_matches:
            matched_key = nonprefix_matches[0]

    if matched_key is not None:
        label = remap_labels[matched_key]
        sec_name = f"{label}"
        if hoc_suffix: sec_name += str(hoc_suffix)
    else:
        sec_name = hoc_label

    return label, sec_name


def read_hoc(
    fname: str = '',
    remap_labels: Optional[Dict[str, str]] = None,
) -> List[_Edge]:
    """Read a .hoc morphology file and return a list of Edge objects.

    Instead of hard-coding section-type names, the function extracts the raw
    label from every ``create <label>`` statement via regex and resolves it
    through *label_map*.  
    
    The map key is compared against the **prefix** of
    the raw label (everything before the first ``_``), case-
    insensitively.  If no key matches, the raw label itself is used as the
    semantic label so that unknown section types are preserved.

    Mapping a label to ``None`` causes those sections to be skipped entirely.

    Args:
        fname (str): Path to the :ref:`hoc_file_format`
        remap_labels (dict[str, str]): 
            Mapping between labels in the :ref:`hoc_file_format` and actual label used in ISF.
            If a label is mapped to ``None``, it is not read in its entirety. This can be useful to e.g.
            create a custom AIS morphology instead of the one in the morphology file, as done in :class:`~single_cell_parser.cell_parser.CellParser._create_ais_Hay2013`

    Returns:
        A list of :class:`_Edge` objects representing the cell morphology
        (axon sections excluded by default).

    Raises:
        IOError: If :paramref:`fname` is not a :ref:`hoc_file_format` file, or if the parsed data are internally inconsistent.
    """
    # Pre-compiled patterns
    _RE_CREATE    = re.compile(r'{create\s+(\w+)}')
    _RE_PT3DADD   = re.compile(r'{pt3dadd\(([^)]+)\)}')  # matches {pt3dadd(anything that isn't a closing bracket)}
    _RE_CONNECT   = re.compile(r'{connect\s+\w+\((\d)\)\s*,\s*(\w+)\(([\d.]+)\)}') # matches {connect(anything that isn't a closing bracket)}


    if not fname.lower().endswith('.hoc'):
        raise IOError('Input file is not a .hoc file!')

    # Build the effective mapping
    label_remapper = HOC_LABEL_MAP
    if remap_labels is not None: label_remapper.update(remap_labels)
    label_remapper = {k.lower(): v for k, v in label_remapper.items()}

    with dbopen(fname, 'r') as fh:
        logger.info("Reading hoc file: %s", fname)
        text = fh.read()

    # Remove /* ... */ comments (including multi-line ones)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

    create_idxs = [m.start() for m in _RE_CREATE.finditer(text)]
    if not create_idxs: return []

    block_texts = [
        text[start:end]
        for start, end in zip(
            create_idxs,
            create_idxs[1:] + [len(text)]
        )
    ]

    sections: list[Dict[str, Any]] = [] 
    insert_order: Dict[str, int] = {}  # hoc_label -> sequential index

    for block in block_texts:
        m_create = _RE_CREATE.search(block)
        if not m_create: continue
        hoc_label: str = m_create.group(1)          # e.g. "dend_1_0"

        label, sec_name = _extract_label_and_name_from_hoc(hoc_label, remap_labels=label_remapper)
        if label.lower() in label_remapper and label_remapper[label.lower()] == None: 
            # Skip this section, as its label is mapped to None
            continue

        if 'Spine' in block: continue

        pt_matches = _RE_PT3DADD.findall(block)    # list of "x,y,z,d" strings
        if not pt_matches: continue  # ignore non-matches

        coords = [list(map(float, s.split(','))) for s in pt_matches]
        edge_pts      = [[c[0], c[1], c[2]] for c in coords]
        diameter_list = [c[3]               for c in coords]

        parent_hoc_label: Optional[str] = None
        parent_connect:   Optional[float] = None
        m_connect = _RE_CONNECT.search(block)
        if m_connect and label.lower() != 'soma':
            if int(m_connect.group(1)) != 0: raise ValueError("HOC file contains sections whose starting point connects at a nonzero relative coordinate.")
            parent_hoc_label = m_connect.group(2)
            parent_connect   = float(m_connect.group(3))

        insert_idx = len(sections)
        insert_order[hoc_label] = insert_idx

        sections.append({
            'label':            label,
            'name':             sec_name,
            'edge_pts':         edge_pts,
            'diameter_list':    diameter_list,
            'parent_name':      parent_hoc_label,
            'parent_connect':   parent_connect,
        })


    edge_list = []
    for sec in sections:
        edge     = _Edge()
        edge.label      = sec['label']
        edge.hocLabel   = sec['name']
        edge.edgePts    = sec['edge_pts']
        edge.diameterList = sec['diameter_list']

        if sec['label'].lower() != 'soma' and sec['parent_name']:
            if sec['parent_name'] not in insert_order:
                raise IOError(f"Logical error: parent '{sec['parent_name']}' of section '{sec['name']}' was not found.")
            edge.parentID      = insert_order[sec['parent_name']]
            edge.parentConnect = sec['parent_connect']
        else:
            edge.parentID = None

        if edge.is_valid(): edge_list.append(edge)
        else: raise IOError(f"Logical error reading hoc file: invalid segment '{sec['name']}'")

    return edge_list


def write_hoc(
    sections, 
    of,
    ):
    """Write a HOC morphology file from a pre-built section directory.

    The soma section is identified by ``parent_name=None`` and is written first
    without a ``connect`` statement.

    Args:
        sections (list of dict): Ordered section records as returned by
            :func:`build_section_directory`, with soma points already complete.
        of (str): Output path for the HOC file.
    """

    def _get_precision(float_nr):
        assert isinstance(float_nr, float), f"This method can only be used on floats. You passed a {type(float_nr)}"
        return len(float_nr.__repr__().split('.')[-1])

    def _get_max_float_padding(sections):
        return max([
            _get_precision(co)
            for sec in sections
            for pt in sec.pts
            for co in pt
        ])
    zero_pad = _get_max_float_padding(sections)
    with open(of, "w") as f:
        for sec in sections:
            sec_name = sec.name()
            parent_connect = sec.parentx
            if not hasattr(sec, "parentID"): 
                # start the file with the soma section without newlines
                f.write(f"{{create {sec_name}}}")
            else:
                f.write(f"\n\n{{create {sec_name}}}")
                f.write(f"\n{{connect {sec_name}(0), {sections[int(sec.parentID)]}({parent_connect:.{zero_pad}f})}}")
            f.write(f"\n{{access {sec_name}}}\n{{nseg = 1}}\n{{pt3dclear()}}")
            for (x, y, z), d in zip(sec.pts, sec.diamList):
                f.write(f"\n{{pt3dadd({x:.{zero_pad}f}, {y:.{zero_pad}f}, {z:.{zero_pad}f}, {d:.{zero_pad}f})}}")
