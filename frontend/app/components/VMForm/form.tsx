import React, {Fragment, useEffect, useMemo, useState} from "react";
import {FormikPropsValues, networkTypeOptions} from "./props";
import {Field} from "formik";
import {faDatabase, faHdd, faServer, faSignature, faTag} from "@fortawesome/free-solid-svg-icons";
import Select from '../Select';
import {
  DomainType,
  SRContentType,
  StorageListFragmentFragment,
  TemplateActions,
  useCurrentUserQuery,
  useISOSCreateVMListQuery,
  useNetworkListQuery,
  usePoolListQuery,
  useStorageListQuery,
  useTemplateListQuery
} from "../../generated-models";
import formatBytes from "../../utils/sizeUtils";
import {useReactSelectFromRecord} from "../../hooks/form";
import messages from "./messages";
import {FormattedMessage} from "react-intl";
import Input from '../Input';
import {faComment} from "@fortawesome/free-solid-svg-icons/faComment";
import {faUser} from "@fortawesome/free-solid-svg-icons/faUser";
import {faKey} from "@fortawesome/free-solid-svg-icons/faKey";
import {Button} from "reactstrap";
import CheckBoxComponent from "../Checkbox";
import {faDesktop} from "@fortawesome/free-solid-svg-icons/faDesktop";
import styled from "styled-components";
import {Fields as ResourceFields} from '../AbstractVMSettingsComponents/fields';
import {TemplateInputField} from "./templateInput";
import {useCurrentUserAndGroups} from "../../hooks/user";
import {UserInputField} from "../MainOwnerForm/userInput";
import {PostInstall} from "./postinstall";
import {VDISizeComponent} from "../AbstractVMSettingsComponents/VDISizeComponent";
import {SRInput} from "../AbstractVMSettingsComponents/srinput";

const H4 = styled.h4`
margin: 20px;
`;

interface Props extends FormikPropsValues {
  taskId?: string;
}

const VMForm: React.FC<Props> = ({taskId, ...props}) => {
  const {data: {pools}} = usePoolListQuery();
  const poolOptions = useReactSelectFromRecord(pools);
  const currentUserAndGroups = useCurrentUserAndGroups();
  const currentUser = useCurrentUserQuery();
  const user = useMemo(() => {
    if (props.values.vmOptions.mainOwner)
      return props.values.vmOptions.mainOwner;
    else if (currentUser.data.currentUser.isAdmin)
      return null;
    else
      return currentUser.data.currentUser.user.id;
  }, [currentUser, props.values.vmOptions.mainOwner]);
  const templateList = useTemplateListQuery();
  const templates = templateList.data.templates.filter(item => {
    return item.myActions.includes(TemplateActions.create_vm)
  });
  const [postInstall, setPostInstall] = useState(false);
  useEffect(() => {
    if (taskId)
      setPostInstall(true);
    else
      setPostInstall(false);
  }, [taskId]);
  const templateOptions = useReactSelectFromRecord(templates);

  const {data: {networks}} = useNetworkListQuery();
  const networkOptions = useReactSelectFromRecord(networks);

  const {data: {isosForInstall}} = useISOSCreateVMListQuery();

  const isoOptions = useReactSelectFromRecord(isosForInstall);

  console.log("Errors:", props.errors);
  console.log("Values:", props.values);
  const currentTemplateCanAutoinstall = useMemo(() => {
    if (!props.values.template)
      return false;

    const template = templates.filter(t => t.ref === props.values.template)[0];
    const {installOptions, domainType} = template;
    return domainType === DomainType.PV && installOptions && installOptions.installRepository && installOptions.arch && installOptions.release && installOptions.distro;

  }, [props.values.template]);
  const hideTemplateElementsStyle = useMemo(() => {
    return props.values.template ? {} : {display: 'none'}
  }, [props.values.template]);
  return (
    <form
      className="form-horizontal"
      onSubmit={props.handleSubmit}
      onReset={props.handleReset}
    >
      {currentUserAndGroups && <Fragment>
        <H4> Ownership </H4>
        <Field
          name='vmOptions.mainOwner'
          component={UserInputField}
          placeholder="Select an owner user/group"
          users={currentUserAndGroups}
        />
      </Fragment>}

      <H4><FormattedMessage {...messages.infrastructure} /></H4>
      <Field name="pool"
             component={Select}
             options={poolOptions}
             placeholder="Select a pool to install on..."
             addonIcon={faServer}
      />
      {props.values.pool && (
        <Fragment>
          <Field name="template"
                 component={TemplateInputField}
                 options={templateOptions}
                 placeholder="Select an OS template to install..."
          />
          <SRInput fieldName="storage"/>

          <Field name="network"
                 component={Select}
                 options={networkOptions}
                 placeholder="Select a network to install on..."
          />
          <Field name="vmOptions.nameLabel"
                 component={Input}
                 placeholder="How you would name this VM"
                 addonIcon={faTag}
          />
          <Field name="vmOptions.nameDescription"
                 component={Input}
                 placeholder="Enter a description (Optional)..."
                 addonIcon={faComment}
          />
          <Field name="autoMode"
                 component={CheckBoxComponent}
                 disabled={!currentTemplateCanAutoinstall}
                 tooltip="Automode"
          >
            <h6> Unattended installation </h6>
          </Field>
          <Fragment>
            {props.values.autoMode && (
              <div>
                <H4 style={{margin: '20px'}}><FormattedMessage {...messages.account} /></H4>
                <Field name="installParams.hostname"
                       component={Input}
                       placeholder="Enter hostname..."
                       addonIcon={faDesktop}
                />
                <Field name="installParams.fullname"
                       component={Input}
                       placeholder="Enter your full name (Optional)..."
                       addonIcon={faSignature}
                />
                <Field name="installParams.username"
                       component={Input}
                       placeholder="Enter username (1-32 latin characters)..."
                       addonIcon={faUser}
                />
                <Field name="installParams.password"
                       component={Input}
                       placeholder="Enter password..."
                       addonIcon={faKey}
                       type="password"
                />
                <Field name="password2"
                       component={Input}
                       placeholder="Repeat password"
                       addonIcon={faKey}
                       type="password"
                />
                <h4><FormattedMessage {...messages.network} /></h4>
                <Field name="networkType"
                       component={Select}
                       options={networkTypeOptions}
                />
                {props.values.networkType === 'static' && (
                  <Fragment>
                    <Field name="installParams.staticIpConfig.ip"
                           component={Input}
                           placeholder={"Enter IP address..."}
                           label={true}
                    >IP:</Field>
                    <Field name="installParams.staticIpConfig.gateway"
                           component={Input}
                           placeholder={"Enter gateway address..."}
                           label={true}
                    >Gateway:</Field>
                    <Field name="installParams.staticIpConfig.netmask"
                           component={Input}
                           placeholder={"Enter netmask address..."}
                           label={true}
                    >Netmask:</Field>
                    <Field name="installParams.staticIpConfig.dns0"
                           component={Input}
                           placeholder={"Enter DNS #1"}
                           label={true}
                    >DNS 1:</Field>
                    <Field name="installParams.staticIpConfig.dns1"
                           component={Input}
                           placeholder={"Enter DNS #2"}
                           label={true}
                    >DNS 2:</Field>
                  </Fragment>
                )
                }
              </div>
            ) || (
              <Field name="iso"
                     component={Select}
                     placeholder="Select ISO image to install from..."
                     options={isoOptions}
              />
            )
            }
            <div style={hideTemplateElementsStyle}>
              <H4><FormattedMessage {...messages.resources} /></H4>
              <ResourceFields namePrefix="vmOptions."/>
              <VDISizeComponent
                fieldName="hddSize"
                user={user}
              />
            </div>
          </Fragment>
        </Fragment>
      )}
      {postInstall && (
        <PostInstall
          taskId={taskId} onClose={() => setPostInstall(false)}/>) ||
      <Button type="submit" block={true} disabled={!props.isValid} primary={true}>
        Create
      </Button>}

    </form>
  )

};
export default VMForm;
