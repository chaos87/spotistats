import { useCubeQuery } from '@cubejs-client/react';
import { Spin, Alert } from 'antd';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const TasteEvolutionChart = () => {
  const { resultSet, isLoading, error } = useCubeQuery({
    measures: ['listens.total_duration'],
    timeDimensions: [
      {
        dimension: 'listens.played_at',
        granularity: 'week',
      },
    ],
    order: {
      'listens.total_duration': 'desc',
    },
    dimensions: ['artists.genres'],
  });

  if (isLoading) {
    return <Spin />;
  }

  if (error) {
    return <Alert message="Error loading data" description={error.toString()} type="error" />;
  }

  if (!resultSet) {
    return null;
  }

  const processData = (resultSet) => {
    const series = resultSet.series();
    const pivot = resultSet.chartPivot();

    // Get top 10 genres
    const genreTotals = series.reduce((acc, s) => {
      const genre = s.key.split(',')[1];
      const total = s.series.reduce((sum, data) => sum + data.value, 0);
      if (!acc[genre]) {
        acc[genre] = 0;
      }
      acc[genre] += total;
      return acc;
    }, {});

    const topGenres = Object.entries(genreTotals)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([genre]) => genre);

    const labels = pivot.map(p => p.x);
    const datasets = topGenres.map(genre => {
      const seriesForGenre = series.find(s => s.key.split(',')[1] === genre);
      return {
        label: genre,
        data: seriesForGenre ? seriesForGenre.series.map(d => d.value) : [],
        fill: false,
        borderColor: '#' + Math.floor(Math.random()*16777215).toString(16)
      };
    });

    return { labels, datasets };
  };

  const chartData = processData(resultSet);

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Taste Evolution: Top 10 Genres by Listen Time',
      },
    },
  };

  return <Line options={options} data={chartData} />;
};

export default TasteEvolutionChart;
