import * as React from 'react';
import {GAccessEntry, User} from "../../generated-models";
import {useCallback, useMemo, useState} from "react";
import {Nav, Col, NavItem, TabContent, ListGroup, Button} from 'reactstrap';
import Row from "reactstrap/lib/Row";
import NavLink from "reactstrap/lib/NavLink";
import classnames from 'classnames';
import TabPane from "reactstrap/lib/TabPane";
import ActionList from "./actionList";
import {DocumentNode} from "graphql";

export interface AccessEntry<T> extends GAccessEntry {
  actions: Array<T>,
  userId: User;
}

interface ACLXenObject<T> {
  isOwner: boolean;
  myActions: Array<T>;
  access: Array<AccessEntry<T>>;
  ref: string;
}

interface Props<T> {
  data: ACLXenObject<T>;
  ALL: T; //ALL action
  mutationNode: DocumentNode,
  mutationName: string,
}


function AccessView<T>({data, ALL, mutationName, mutationNode}: Props<T>) {
  const [activeTab, setActiveTab] = useState("you");
  const toggleTab = useCallback((tab: string) => {
    if (activeTab !== tab) {
      setActiveTab(tab);
    }
  }, [activeTab]);
  return (
    <Row>
      <Col xs={6} sm={4} md={4}>
        <Nav tabs={true} vertical={true} pills={true}>
          <NavItem>
            <NavLink
              className={classnames({active: activeTab === 'you'})}
              onClick={() => {
                toggleTab('you')
              }
              }
            >
              You
            </NavLink>
          </NavItem>
          {data.access.map(item => (
            <NavItem>
              <NavLink
                className={classnames({active: activeTab === item.userId.id})}
                onClick={() => {
                  toggleTab(item.userId.id)
                }}
              >
                {item.userId.name}
              </NavLink>
            </NavItem>
          ))}
        </Nav>
      </Col>
      <Col xs="6" sm="6" md="6">
        <TabContent activeTab={activeTab}>
          <TabPane tabId="you">
            <ActionList
              actions={data.myActions}
              isOwner={data.isOwner}
              refs={[data.ref]}
              mutationNode={mutationNode}
              mutationName={mutationName}
              ALL={ALL}
            />
          </TabPane>
          {data.access.map(item => (
            <TabPane tabId={item.userId.id}>
              <ActionList
                actions={item.actions}
                user={item.userId}
                isOwner={data.isOwner}
                refs={[data.ref]}
                mutationNode={mutationNode}
                mutationName={mutationName}
                ALL={ALL}
              />
            </TabPane>
          ))}
        </TabContent>
      </Col>
    </Row>
  );

}

export default AccessView;
