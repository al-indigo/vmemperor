import Button from '@material-ui/core/Button'
import ArrowRightIcon from '@material-ui/icons/ArrowRightAlt'
import { defaultDataIdFromObject } from 'apollo-cache-inmemory'
import gql from 'graphql-tag'
import { History } from 'history'
import * as React from 'react'
import { useMutation } from 'react-apollo-hooks'
import styled from 'styled-components'
import * as fragments from '../../graphql/fragments'
import { User, CompleteGroupButtonMutation } from '../../graphql/types'

const Style = styled.div`
  position: fixed;
  right: 10px;
  bottom: 10px;

  button {
    min-width: 50px;
    width: 50px;
    height: 50px;
    border-radius: 999px;
    background-color: var(--secondary-bg);
    color: white;
  }
`

const mutation = gql`
  mutation CompleteGroupButtonMutation(
    $userIds: [ID!]!
    $groupName: String!
    $groupPicture: String
  ) {
    addGroup(userIds: $userIds, groupName: $groupName, groupPicture: $groupPicture) {
      ...Chat
    }
  }
  ${fragments.chat}
`

interface CompleteGroupButtonProps {
  history: History
  users: User.Fragment[]
  groupName: string
  groupPicture: string
}

export default ({ history, users, groupName, groupPicture }: CompleteGroupButtonProps) => {
  const addGroup = useMutation<
    CompleteGroupButtonMutation.Mutation,
    CompleteGroupButtonMutation.Variables
  >(mutation, {
    variables: {
      userIds: users.map(user => user.id),
      groupName,
      groupPicture,
    },
    update: (client, { data: { addGroup } }) => {
      client.writeFragment({
        id: defaultDataIdFromObject(addGroup),
        fragment: fragments.chat,
        fragmentName: 'Chat',
        data: addGroup,
      })
    },
  })

  const onClick = () => {
    addGroup().then(() => {
      history.push('/chats')
    })
  }

  return (
    <Style className="CompleteGroupButton">
      <Button variant="contained" color="secondary" onClick={onClick}>
        <ArrowRightIcon />
      </Button>
    </Style>
  )
}
