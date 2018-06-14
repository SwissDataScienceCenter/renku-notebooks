import React, { Component } from 'react';
import './App.css';
import Notebooks from './notebooks';

class App extends Component {
  render() {
    return (
      <div className="container-fluid">
        <Notebooks.Admin statusUrl="/services/notebooks/" stopServerUrl="/services/notebooks/stop/" />
      </div>
    );
  }
}

export default App;
