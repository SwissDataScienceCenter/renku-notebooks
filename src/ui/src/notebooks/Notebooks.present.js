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
import { Row, Col } from 'reactstrap';
import { Table } from 'reactstrap';

class NotebookServerRow extends Component {
  render() {
    const name = this.props.name;
    const url = this.props.url
    return <tr>
      <td>{name}</td>
      <td><a className="btn btn-primary" role="button" href={url}>Connect</a></td>
      <td>
        <button className="btn btn-primary" type="button"
          onClick={(e) => this.props.onStopServer(name)}>Stop</button></td>
    </tr>
  }
}

class NotebookServers extends Component {
  render() {
    const servers = this.props.servers;
    const serverKeys = Object.keys(servers).sort();
    if (serverKeys.length < 1) return <p>No servers</p>
    const rows = serverKeys.map((k, i) =>
      <NotebookServerRow key={i} onStopServer={this.props.onStopServer} {...servers[k]} />
    )
    return <Table size={"sm"}>
        <thead>
          <tr><th>Name</th><th>Connect</th><th>Stop</th></tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
    </Table>
  }
}

class NotebooksAdmin extends Component {
  render() {
    const status = this.props.status;
    const servers = (status) ? status.servers || {} : {};
    return [
      <Row key="header"><Col><h1>Notebook Server Status</h1></Col></Row>,
      <Row key="servers">
        <Col md={10} lg={8}>
          <NotebookServers servers={servers} onStopServer={this.props.onStopServer}/>
        </Col>
      </Row>,
    ]
  }
}


export { NotebooksAdmin };
