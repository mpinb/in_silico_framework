import React from 'react';
import createScatterplot from 'regl-scatterplot';
import { viridisColormapReverse } from '../core/colorManager';
import CoordinatedView from '../core/coordinatedView';

import { deepCopy, getValueOrDefault } from '../core/utilCore';
import { SelectionEvent } from '../core/interactionEvent';



const styleBackground = {
  backgroundColor: "white",
  color: "white"
}

class ReglScatterPlot extends CoordinatedView {
  constructor(props) {
    super(props);

    this.myRef = React.createRef();

    this.has_color = this.dataColumn.length === 3 && props.embedding === "none";
    this.embedding = props.embedding;

    this.scatterplot = undefined;
  }

  getData() {
    return {
      table: this.getDataColumns()
    }
  }


  updateSelection() {
    try {
      const points = this.scatterplot.get("points");
      if (!points.length) {
        return;
      }
      this.scatterplot.select(deepCopy(this.selection), { preventEvent: true });
      
      if (this.dataTable === "Abstract DataFrame") {
        const request_data = {
          table: this.dataTable,
          view_name: this.name,
          indices: deepCopy(this.selection)
        }
        this.dataManager.setIndicesSelection(request_data);
      }

    } catch (e) {
      console.log(e);
    }
  }


  handleSelect(eventArgs) {
    this.notifyInteraction(new SelectionEvent(this.name, this.dataTable).setIndices(eventArgs.points));
  }


  handleDeselect() {
    this.notifyInteraction(new SelectionEvent(this.name, this.dataTable).setDeselect());
  }


  render() {
    return <div style={styleBackground}><canvas ref={this.myRef} width={this.width} height={this.height} /></div>
  }


  componentDidMount() {
    const canvas = this.myRef.current;
    canvas.fillStyle = "white";
    if (this.dataColumn.length < 2) {
      return;
    }

    const { width, height } = canvas.getBoundingClientRect();

    this.scatterplot = createScatterplot({
      canvas,
      width,
      height,
      pointSize: getValueOrDefault(this.configuration.pointSize, 2),
      lassoColor: "#ffa500",
      performanceMode: getValueOrDefault(this.configuration.performanceMode, false),
      pointColor: this.has_color ? viridisColormapReverse : ["#4682b4"],
      opacityInactiveMax: getValueOrDefault(this.configuration.pointOpacity, 0.3),
      colorBy: this.has_color ? 'valueA' : undefined,
      keyMap: { alt: 'lasso', shift: 'rotate' }
    });

    let format = this.embedding === "PCA" ? "flat-normalized-PCA" : "flat-normalized";
    let that = this;
    this.dataManager.loadValues((data) => {
      let values = data.values;
      if (this.has_color) {
        values = values.map(v => [v[0], v[1], 0.5 * (v[2] + 1)]);
      }
      that.scatterplot.draw(values);

      that.scatterplot.subscribe("select", this.handleSelect.bind(this));
      that.scatterplot.subscribe("deselect", this.handleDeselect.bind(this));
    }, this.dataTable, [], this.dataColumn, format);

    super.componentDidMount();
  }

  componentWillUnmount() {
    super.componentWillUnmount();
    try {
      this.scatterplot.destroy();
    } catch (error) {
      console.log(error);
    }

  }
}

export default ReglScatterPlot