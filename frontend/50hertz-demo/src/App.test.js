import { render, screen } from '@testing-library/react';
import App from './App';

test('renders page and check for status', () => {
  render(<App />);
  const linkElement = screen.getByText(/Status/i);
  expect(linkElement).toBeInTheDocument();
});
