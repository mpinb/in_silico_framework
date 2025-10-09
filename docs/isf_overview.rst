.. graphviz::
   :alt: High-level ISF overview
   :align: center

    digraph "sphinx-ext-graphviz" {
      compound=true
      rankdir="LR"
      concentrate=true
      ranksep=1
      graph [fontname="Verdana", fontsize="12"]
      node [fontname="Verdana", fontsize="12", shape=box]
      edge [fontname="Sans", fontsize="9"]

        input [
            label="Empirical data"
            style=rounded
            color="var(--md-default-fg-color--light, grey)"
            width=2
            ]
        neuron [
            label="Neuron models"
            href="tutorials.html#neuron-models"
            style=rounded
            color="var(--md-default-fg-color--light, grey)"
            width=2
            ]
        msm [
            label="Network-embedded\n neuron models"
            href="tutorials.html#network-embedded-neuron-models"
            style=rounded
            color="var(--md-default-fg-color--light, grey)"
            width=2
            ]
        analysis [
            label="Manipulations &\nreduced models"
            href="tutorials.html#manipulations-reduced-models"
            style=rounded
            color="var(--md-default-fg-color--light, grey)"
            width=2
            ]
        output [
            label="Mechanistic explanation"
            style=rounded
            color="var(--md-default-fg-color--light, grey)"
            wdith=2
            ]

        subgraph cluster_input {
            color=None
            label="INPUT"
            input
        }
        
        subgraph cluster_output {
            color=None
            label="OUTPUT"
            output
        }

        {
            rank=same
            neuron -> msm -> analysis [constraint=false]
        }

        input -> neuron     [tailport=e, headport=w]
        input -> msm        [tailport=e, headport=w]
        input -> analysis   [tailport=e, headport=w]
        neuron -> output    [headport=w, tailport=e, arrowhead=none]
        msm -> output       [headport=w, tailport=e]
        analysis -> output  [headport=w, tailport=e, arrowhead=none]
        output -> input [
            headport=s
            tailport=s
            constraint=false
            color="var(--md-accent-fg-color, red)"
            fontcolor="var(--md-accent-fg-color, red)"
            label=PREDICTION
            ]
        }