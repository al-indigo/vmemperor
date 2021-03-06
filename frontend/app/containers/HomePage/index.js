/*
 * HomePage
 *
 * This is the first thing users see of our App, at the '/' route
 *
 * NOTE: while this component should technically be a stateless functional
 * component (SFC), hot reloading does not currently support SFCs. If hot
 * reloading is not a necessity for you then you can refactor it and remove
 * the linting exception.
 */

import React from 'react';
import {Redirect} from 'react-router-dom';
import { FormattedMessage } from 'react-intl';
import messages from './messages';

const HomePage = () => {
  console.log('in homepage');
  return <Redirect to="/vms"/>;
};

export default HomePage;
