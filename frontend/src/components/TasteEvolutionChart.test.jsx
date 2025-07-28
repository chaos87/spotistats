import { render } from '@testing-library/react';
import TasteEvolutionChart from './TasteEvolutionChart';
import { useCubeQuery } from '@cubejs-client/react';

jest.mock('@cubejs-client/react');
jest.mock('react-chartjs-2');
jest.mock('chart.js');

test('renders learn react link', () => {
  useCubeQuery.mockImplementation(() => ({
    resultSet: {
        series: () => [],
        chartPivot: () => [],
    },
    isLoading: false,
    error: null,
  }));
  render(<TasteEvolutionChart />);
});
