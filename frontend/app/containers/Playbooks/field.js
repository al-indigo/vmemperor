import React, {Component} from 'react';
import PropTypes from 'prop-types';
import {AvGroup, AvFeedback, AvInput} from 'availity-reactstrap-validation';
import {Col, FormText, Label} from 'reactstrap';

const colSizes = ['xs', 'sm', 'md', 'lg', 'xl'];

export default class Field extends Component {
  static propTypes = Object.assign({}, AvInput.propTypes, {
    label: PropTypes.node,
    labelHidden: PropTypes.bool,
    disabled: PropTypes.bool,
    readOnly: PropTypes.bool,
    id: PropTypes.string,
    inputClass: PropTypes.string,
    labelClass: PropTypes.string,
    helpMessage: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.object,
    ]),
    errorMessage: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.object,
    ]),
    labelAttrs: PropTypes.object,
    groupAttrs: PropTypes.object,
    grid: PropTypes.object,
  });

  static contextTypes = {
    FormCtrl: PropTypes.object.isRequired,
  };

  static childContextTypes = {
    FormCtrl: PropTypes.object.isRequired,
  };

  getChildContext() {
    this.FormCtrl = {...this.context.FormCtrl};
    const registerValidator = this.FormCtrl.register;
    this.FormCtrl.register = (input, updater = input && input.forceUpdate) => {
      registerValidator(input, () => {
        this.forceUpdate();
        if (updater) updater();
      });
    };
    return {
      FormCtrl: this.FormCtrl,
    };
  }

  render() {
    let row = false;
    const col = {};
    const labelCol = {};
    const {
      helpMessage,
      label,
      labelHidden,
      inputClass,
      labelClass,
      children,
      id = this.props.name,
      size,
      disabled,
      readOnly,
      grid,
      labelAttrs,
      groupAttrs,
      ...attributes
    } = this.props;

    if (grid) {
      colSizes.forEach(colSize => {
        if (grid[colSize]) {
          row = true;
          const sizeNum = parseInt(grid[colSize], 10);
          col[colSize] = sizeNum;
          labelCol[colSize] = 12 - sizeNum;
        }
      });
    }

    const input = (<AvInput
      id={id}
      className={inputClass}
      size={size}
      disabled={disabled}
      readOnly={readOnly}
      {...attributes}
    >
      {children}
    </AvInput>);

    const validation = this.context.FormCtrl.getInputState(this.props.name);

    const feedback = validation.errorMessage ? (<AvFeedback>{validation.errorMessage}</AvFeedback>) : null;
    const help = helpMessage ? (<FormText>{helpMessage}</FormText>) : null;

    return (
      <AvGroup disabled={disabled} row={row} {...groupAttrs}>
        {label && <Label
          for={id}
          className={labelClass}
          hidden={labelHidden}
          size={size}
          {...labelCol}
          {...labelAttrs}
        >
          {label}
        </Label>}
        {row ? <Col {...col}>{input}{feedback}{help}</Col> : input}
        {!row && feedback}
        {!row && help}
      </AvGroup>
    );
  }
}
