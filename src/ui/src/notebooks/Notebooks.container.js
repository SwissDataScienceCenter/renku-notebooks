/*!
 * Copyright 2018 - Swiss Data Science Center (SDSC)
 * A partnership between École Polytechnique Fédérale de Lausanne (EPFL) and
 * Eidgenössische Technische Hochschule Zürich (ETHZ).
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import React, { Component } from 'react';
import { NotebooksAdmin as NotebooksAdminPresent } from './Notebooks.present';


class NotebooksAdmin extends Component {
  constructor(props){
    super(props);
    this.state = {status: null};
    this.onStopServer = this.doStopServer.bind(this);
  }

  async doStopServer(serverName) {
    const url = `${this.props.stopServerUrl}/${serverName}`;
    const r = await fetch(url, {credentials: 'include', method: 'DELETE'});
    await this.retreiveStatus();
  }

  componentDidMount() {
    this.retreiveStatus();
  }

  async retreiveStatus() {
    const url = this.props.statusUrl;
    const r = await fetch(url, {credentials: 'include'});
    const status = await r.json();
    this.setState({url, status});
  }
  render() {
    return <NotebooksAdminPresent status={this.state.status} onStopServer={this.onStopServer} />
  }
}


export { NotebooksAdmin };
