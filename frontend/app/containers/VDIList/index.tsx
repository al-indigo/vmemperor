/**
 * Remember to put every new local query in app.tsx initialization, so that
 * it could be initialized with empty local state
 */
import StatefulTable, {ColumnType} from "../StatefulTable";
import {
  VDIListDocument,
  VDIListFragmentFragment, VDIListFragmentFragmentDoc, VDIListUpdateDocument,
  VDITableSelectAllDocument,
  VDITableSelectDocument,
  VDITableSelectionDocument,
  useVDIListQuery,
  useVDITableSelectionQuery, VDIAccessSetMutationDocument, VDIActions, DeleteVDIDocument,
} from "../../generated-models";
import {nameFormatter} from "../../utils/formatters";
import filterFactory, {textFilter} from 'react-bootstrap-table2-filter';
import {RouteComponentProps} from "react-router";
import {getStateInfoAndTypeFromCache, handleAddRemove} from "../../utils/cacheUtils";
import * as React from "react";
import {Fragment, Reducer, ReducerState, useCallback, useReducer} from 'react';
import {
  readCacheObject,
  selectedForSetActionReducer,
  SelectedForSetActionState, selectedForTrashReducer, SelectedForTrashState
} from "../../utils/componentStateReducers";
import {ListAction} from "../../utils/reducer";
import {Set} from 'immutable';
import {useTableSelectionInInternalState, useUpdateInternalStateWithSubscription} from "../../hooks/listSelectionState";
import {useApolloClient} from "react-apollo-hooks";
import {ButtonGroup, ButtonToolbar} from "reactstrap";
import SetAccessButton from "../../components/SetAccessButton";
import RecycleBinButton from "../../components/RecycleBinButton";

type VDIColumnType = ColumnType<VDIListFragmentFragment>;

const columns: VDIColumnType[] = [
  {
    dataField: "nameLabel",
    text: "Name",
    filter: textFilter(),
    headerFormatter: nameFormatter,
    headerClasses: 'align-self-baseline'
  }
];


interface State extends SelectedForSetActionState, SelectedForTrashState {

}

type VDIListReducer = Reducer<State, ListAction>;

const initialState: ReducerState<VDIListReducer> = {
  selectedForSetAction: Set.of<string>(),
  selectedForTrash: Set.of<string>(),
};

const VDIs: React.FunctionComponent<RouteComponentProps> = ({history}) => {
  const {data: {vdis}} = useVDIListQuery();
  const client = useApolloClient();
  const readVDI = useCallback((ref) => {
    return readCacheObject<VDIListFragmentFragment>(client, VDIListFragmentFragmentDoc, "GVDI", ref);
  }, [client]);

  const reducer: VDIListReducer = (state, action) => {
    const [type, info] = getStateInfoAndTypeFromCache(action, readVDI);
    return {
      ...selectedForSetActionReducer(type, info, state),
      ...selectedForTrashReducer(VDIActions.destroy, type, info, state)
    }
  };
  const {data: {selectedItems}} = useVDITableSelectionQuery();
  const [state, dispatch] = useReducer<VDIListReducer>(reducer, initialState);
  useTableSelectionInInternalState(dispatch, selectedItems);
  useUpdateInternalStateWithSubscription(dispatch, VDIListUpdateDocument, VDIListDocument, client, "vdis");

  const onDoubleClick = useCallback((e: React.MouseEvent, row: VDIListFragmentFragment, index) => {
    e.preventDefault();
    history.push(`/vdi/${row.ref}`);
  }, [history]);
  return (
    <Fragment>
      <ButtonToolbar>
        <ButtonGroup size="lg">
          <SetAccessButton
            ALL={VDIActions.ALL}
            state={state}
            mutationName="vdiAccessSet"
            mutationNode={VDIAccessSetMutationDocument}
            readCacheFunction={readVDI}/>
        </ButtonGroup>
        <ButtonGroup size="lg">
          <RecycleBinButton
            destroyMutationName="vdiDelete"
            state={state}
            destroyMutationDocument={DeleteVDIDocument}
            readCacheFunction={readVDI}/>
        </ButtonGroup>
      </ButtonToolbar>
      <StatefulTable
        keyField="ref"
        data={vdis}
        tableSelectOne={VDITableSelectDocument}
        tableSelectMany={VDITableSelectAllDocument}
        tableSelectionQuery={VDITableSelectionDocument}
        columns={columns}
        onDoubleClick={onDoubleClick}
        onSelect={(key, isSelect) => dispatch({
          type: isSelect ? "Add" : "Remove",
          ref: key,
        })}
        props={{
          striped: true,
          hover: true,
          filter: filterFactory(),
        }}
      />
    </Fragment>
  );


};

export default VDIs;