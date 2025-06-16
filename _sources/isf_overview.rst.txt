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
            label="Empirical data", 
            style=rounded, 
            color="var(--md-default-fg-color--light, grey)"
            width=2]
        neuron [
            label="Neuron models",
            href="tutorials/1. neuron models/1.3 Generation.html",
            style=rounded, 
            color="var(--md-default-fg-color--light, grey)"
            width=2]
        msm [
            label="Network-embedded \n neuron models", 
            href="tutorials/3. multiscale models/3.1 Multiscale modeling.html",
            style=rounded, 
            color="var(--md-default-fg-color--light, grey)"
            width=2]
        red [
            label="Reduced models",
            href="tutorials/4. reduced models/4.1 Generalized Linear Models.html",
            style=rounded, 
            color="var(--md-default-fg-color--light, grey)"
            width=2]
        output [
            label="Mechanistic explanation",
            style=rounded, 
            color="var(--md-default-fg-color--light, grey)"
            wdith=2]

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
            neuron -> msm -> red [constraint=false]
        }

        input -> neuron [tailport=e, headport=w]
        input -> msm [tailport = e, headport=w]
        input -> red [tailport=e, headport=w]
        neuron -> output [headport=w, tailport=e]
        msm -> output [headport=w, tailport=e]
        red -> output [headport=w, tailport=e]
        output -> input [
            headport=s, 
            tailport=s, 
            constraint=false, 
            color="var(--md-accent-fg-color, red)", 
            fontcolor="var(--md-accent-fg-color, red)", 
            label=PREDICTION
            ]
        }
