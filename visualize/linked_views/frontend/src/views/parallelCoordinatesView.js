import React from 'react';
import Plot from 'react-plotly.js';
import CoordinatedView from '../core/coordinatedView';
import { SelectionEvent } from '../core/interactionEvent';
import { getValueOrDefault } from '../core/utilCore';
import { deepCopy } from '../core/utilCore';



const empty_traces = [
  {
    type: 'parcoords',
    line: {
      color: "blue",
    },
    dimensions: [
      { range: [-1, 1], label: 'A', values: [0] },
      { range: [-1, 1], label: 'B', values: [0] },
      { range: [-1, 1], label: 'C', values: [0] },
    ],
  },
];


function makeNestedArray(constraints) {
  if (!Array.isArray(constraints[0])) {
    return [constraints];
  } else {
    return constraints;
  }
}

function getConstraintsCopy(toCopy) {
  if (toCopy.length === 0) {
    return [];
  } else {
    const copiedConstraints = [];
    const nested = makeNestedArray(toCopy);
    for (let k = 0; k < nested.length; k++) {
      copiedConstraints.push([nested[k][0], nested[k][1]])
    }
    return copiedConstraints;
  }
}

function constraintIsDefined(constraintrange) {
  if (constraintrange === undefined) {
    return false;
  } else {
    return constraintrange.length !== 0;
  }
}

class ParallelCoordinates extends CoordinatedView {
  constructor(props) {
    super(props);

    this.state = {
      traces: empty_traces,
    }
    this.constraints = undefined;

    this.nameMapping = getValueOrDefault(this.configuration.nameMapping, {});
    this.marginLeft = getValueOrDefault(this.configuration.marginLeft, 50);
    this.marginRight = getValueOrDefault(this.configuration.marginRight, 50);
    this.marginTop = getValueOrDefault(this.configuration.marginTop, 50);
    this.marginBottom = getValueOrDefault(this.configuration.marginBottom, 50);
  }

  buildDimensions(data, values, nameMapping) {

    const getLabel = (name) => {
      if (nameMapping[name]) {
        return nameMapping[name]
      } else {
        return name;
      }
    }

    let dimensions = [];
    for (let col_idx = 0; col_idx < data.columns.length; col_idx++) {
      let column_name = data.columns[col_idx];
      let range = [data.data_ranges.min[col_idx], data.data_ranges.max[col_idx]]
      let valuesForColumn = values.map(x => x[column_name]);
      if (valuesForColumn.length) {
        range = [Math.min(...valuesForColumn), Math.max(...valuesForColumn)];
      }
      const label = getLabel(column_name);

      let constraintrange = [];
      if (this.constraints !== undefined) {
        constraintrange = getConstraintsCopy(this.constraints[label]);
      }

      dimensions.push({
        "range": range,
        "constraintrange": constraintrange,
        "label": label,
        "values": valuesForColumn
      });
    }
    return dimensions;
  }

  updateSelection() {
    this.buildTraces(this.selection);
    
    if (this.dataTable === "pandas_df") {
      const request_data = {
        table: this.dataTable,
        view_name: this.name,
        indices: deepCopy(this.selection)
      }
      this.dataManager.setIndicesSelection(request_data);
    }
  }

  componentWillUnmount() {
    super.componentWillUnmount();
  }


  buildTraces(selectedIndices) {
    let values = this.data.values;

    const indexSet = new Set(selectedIndices);
    const indicator = [];
    for (let i = 0; i < values.length; i++) {
      if (indexSet.has(i) || indexSet.size === 0) {
        indicator.push(1);
      } else {
        indicator.push(0);
      }
    }

    let traces = [
      {
        type: 'parcoords',
        line: {
          color: values.map((_, index) => {
            return indicator[index];
          }),
          colorscale: [[0, 'rgba(150, 150, 150, .2)'], [1, 'rgba(0, 0, 255, 1)']],
        },
        labelangle: 0,
        dimensions: this.buildDimensions(this.data, values, this.nameMapping),
      }];

    this.setState((state, props) => {
      state.traces = traces;
      return state;
    });
  }

  loadTraces(selectedIndices = []) {
    let that = this;
    this.dataManager.loadValues((data) => {
      that.data = data;
      that.constraints = undefined;
      that.buildTraces(selectedIndices);
    }, this.dataTable, [], this.dataColumn, "expanded");
  }

  componentDidMount() {
    this.loadTraces();
    super.componentDidMount();
  }

  checkConstraintsChanged(dimensions) {

    let changed = false;
    if (this.constraints === undefined) {
      // register initial constraints for all dimensions
      this.constraints = {};
      for (let i = 0; i < dimensions.length; i++) {
        const label = dimensions[i].label;
        const constraintrange = dimensions[i].constraintrange;
        if (constraintrange.length !== 0) {
          throw Error("expected empty constraints on load");
        }
        this.constraints[label] = [];
      }
    } else {
      // update if changed
      for (let i = 0; i < dimensions.length; i++) {
        const label = dimensions[i].label;
        const previous = this.constraints[label];
        let current = dimensions[i].constraintrange;
        if (current === undefined) {
          current = [];
        }
        if (previous.length === 0 && current.length !== 0) {
          changed = true;
          this.constraints[label] = getConstraintsCopy(current);
        } else if (previous.length !== 0 && current.length === 0) {
          changed = true;
          this.constraints[label] = [];
        } else if (previous.length !== 0 && current.length !== 0) {
          const previousNested = makeNestedArray(previous);
          const currentNested = makeNestedArray(current);
          if (previousNested.length !== currentNested.length) {
            changed = true;
            this.constraints[label] = getConstraintsCopy(currentNested)
          } else {
            for (let k = 0; k < previousNested.length; k++) {
              changed = changed || previousNested[k][0] !== currentNested[k][0] || previousNested[k][1] !== currentNested[k][1];
            }
            if (changed) {
              this.constraints[label] = getConstraintsCopy(currentNested);
            }
          }
        }
      }
    }
    return changed;
  }

  handleEvent(eventData) {
    const dimensions = eventData.data[0].dimensions;
    const constraintsChanged = this.checkConstraintsChanged(dimensions);
    //console.log(constraintsChanged, this.constraints, this.selection);
    if (!constraintsChanged) {
      return;
    }

    let filtered_indices = dimensions[0].values.map((value, index) => { return index });
    for (let i = 0; i < dimensions.length; i++) {
      const constraintrange = dimensions[i].constraintrange;
      if (constraintIsDefined(constraintrange)) {
        const constraints = makeNestedArray(constraintrange);
        const values = dimensions[i].values;

        let indicesMatchingConstraints = []
        for (let k = 0; k < constraints.length; k++) {
          const min = constraints[k][0];
          const max = constraints[k][1];

          indicesMatchingConstraints = filtered_indices.reduce((accumulator, index) => {
            const value = values[index];
            if (value >= min && value <= max) {
              accumulator.push(index);
            }
            return accumulator;
          }, indicesMatchingConstraints);
        }
        filtered_indices = indicesMatchingConstraints;
      }
    }
    this.notifyInteraction(new SelectionEvent(this.name, this.dataTable).setIndices(filtered_indices));
  }

  render() {
    const layout = {
      margin: {
        l: this.marginLeft,
        r: this.marginRight,
        t: this.marginTop,
        b: this.marginBottom,
      },
      width: this.width,
      height: this.height
    }

    return <Plot
      data={this.state.traces}
      layout={layout}
      onUpdate={this.handleEvent.bind(this)}
    />
  };
};

export default ParallelCoordinates;