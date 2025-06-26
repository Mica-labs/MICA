import React from 'react';

import CommonError from './error';
import invoker from './invoker';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  // eslint-disable-next-line no-unused-vars
  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  // eslint-disable-next-line no-unused-vars
  componentDidCatch(error, errorInfo) {
    // You can also log the error to an error reporting service
    console.log(this.props.level, error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.global) {
        invoker('fail');
        return null;
      }
      // You can render any custom fallback UI
      return <CommonError error={this.state.error} />;
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
