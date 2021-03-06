import {ResourceFormValues} from "../AbstractVMSettingsComponents/schema";
import {FormikProps} from "formik";
import * as React from "react";
import {Alert, Button, Form, FormFeedback} from "reactstrap";
import {Fields} from "../AbstractVMSettingsComponents/fields";
import ButtonGroup from "reactstrap/lib/ButtonGroup";
import {ReactNode} from "react";

interface Props<T> extends FormikProps<T> {
  children?: ReactNode;
}

export function ApplyResetForm<T>
(props: Props<T>) {
  return (
    <Form onSubmit={props.handleSubmit}>
      {props.children}
      <ButtonGroup>
        <Button type="submit" disabled={!props.isValid} className="float-right" color="primary">
          Apply
        </Button>
        <Button className="float-right" color="danger" onClick={() => props.resetForm()}>
          Reset
        </Button>
      </ButtonGroup>
      {props.status && props.status.error && (
        <Alert color={"danger"}>
          {props.status.error}
        </Alert>
      )}
    </Form>
  )
};
