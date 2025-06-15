.. graphviz::
    :caption: Overview of file formats.
    :alt: How Sphinx and GraphViz Render the Final Document
    :align: center

     digraph "sphinx-ext-graphviz" {
        compound=true;
        rankdir="TB";
        graph [fontname="Verdana", fontsize="12"];
        node [fontname="Verdana", fontsize="12"];
        edge [fontname="Sans", fontsize="9"];

        morphology_file [label="morphology.hoc", shape="note", fontcolor=black,
                 fillcolor="white", style=filled,
                 xref=":ref:`hoc_file_format`"];
        syn [label=".syn", shape="note", fontcolor=black,
                 fillcolor="white", style=filled,
                 xref=":ref:`syn_file_format`"];
        con [label=".con", shape="note", fontcolor=black,
                 fillcolor="white", style=filled,
                 xref=":ref:`con_file_format`"];
        netp [label="network.param", shape="note", fontcolor=black,
                fillcolor="white", style=filled,
                xref=":ref:`network_parameters_format`"];
        neup [label="neuron.param", shape="note", fontcolor=black,
                fillcolor="white", style=filled,
                xref=":ref:`cell_parameters_format`"];
        biophys_df [label="biophys.df", shape="note", fontcolor=black,
                 fillcolor="white", style=filled];

        scim [label="single_cell_input_mapper", shape="folder",
                 xref=":py:mod:`singlecell_input_mapper`"];
        scim2 [label="single_cell_input_mapper", shape="folder",
                 xref=":py:mod:`singlecell_input_mapper`"];
        scp [label="single_cell_processor", shape="folder",
                xref=":py:mod:`single_cell_parser`"];
        simrun [label="simrun", shape="folder",
                 xref=":py:mod:`simrun`"];
        biophysics_fitting [label="biophysics_fitting", shape="folder",
                 xref=":py:mod:`biophysics_fitting`"];

        subgraph cluster_syncon {
		style=filled;
                rankdir="LR";
		color=lightgrey;
		con [constraint=false];
                syn [constraint=false];
		label = "";
	}

        morphology_file -> biophysics_fitting ;
        biophysics_fitting -> biophys_df ;
        biophys_df -> scp ;
        scp -> neup ;
        neup -> simrun ;

        morphology_file -> scim;
        scim -> con [lhead=cluster_syncon];
        con -> scim2 [ltail=cluster_syncon];
        scim2 -> netp ;
        netp -> simrun ;

     }