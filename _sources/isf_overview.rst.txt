.. 
    graphviz diagram overview of ISF
    I fyou want to change this, I recommend adapting it in an inteactive viewer instead of rebuilding constantly
    E.g.: https://dreampuf.github.io/GraphvizOnline/?engine=dot


.. graphviz::
   :alt: High-level ISF overview
   :align: center

    digraph "sphinx-ext-graphviz" {
        rankdir="LR"
        ranksep=1
        concentrate=true
        graph [fontname="Verdana", fontsize="12"]
        node [fontname="Verdana", fontsize="12", shape=box]

        obs [
            label="In vivo observation"
            style=rounded
            color="var(--md-accent-fg-color, red)"
            width=2
        ]
        pred [
            label="Testable prediction"
            style=rounded
            color="var(--md-accent-fg-color, red)"
            width=2
        ]
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
        expl [
            label="Mechanistic\nexplanation"
            style=rounded
            color="var(--md-default-fg-color--light, grey)"
            width=2
        ]

        
        { rank=max; pred }
        { rank=min; obs }
        
        input -> neuron     [tailport=e, headport=w]
        input -> msm        [tailport=e, headport=w]
        input -> analysis   [tailport=e, headport=w]
        neuron -> expl    [headport=w, tailport=e, arrowhead=none]
        msm -> expl       [headport=w, tailport=e]
        analysis -> expl  [headport=w, tailport=e, arrowhead=none]

        neuron -> msm -> analysis [constraint=false]

        obs -> input [constraint=false]
        expl -> pred [constraint=false]
            obs -> pred  [
            color="var(--md-accent-fg-color, red)"
            fontcolor="var(--md-accent-fg-color, red)"
            dir=back
        ]

    }