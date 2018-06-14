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

 /**
  *  renku-ui
  *
  * Tests for the notebook server component
  */

import React from 'react';
import ReactDOM from 'react-dom';

import { NotebooksAdmin } from './Notebooks.present';

const status = {
  "admin": false,
  "groups": [],
  "kind": "user",
  "last_activity": "2018-03-27T13:37:45.340275",
  "name": "demo",
  "pending": null,
  "server": null,
  "servers": {
    "demo-test-review-master-lz10x0": {
      "name": "demo-test-review-master-lz10x0",
      "url": "/user/demo/demo-test-review-master-lz10x0/"
    }
  }
};

const onStopServer = () => console.log("Clicked stop server.");

describe('rendering', () => {
  it('renders home without crashing', () => {
    const div = document.createElement('div');
    ReactDOM.render(<NotebooksAdmin status={status} onStopServer={onStopServer} />, div);
  });
});
