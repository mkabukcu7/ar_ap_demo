import {
  Card,
  CardHeader,
  Text,
  Badge,
  ProgressBar,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useARMetrics } from '../api/hooks';

const useStyles = makeStyles({
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: tokens.spacingHorizontalM,
    padding: tokens.spacingVerticalS,
  },
  metric: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalXS,
    padding: tokens.spacingHorizontalM,
    borderRadius: tokens.borderRadiusMedium,
    background: tokens.colorNeutralBackground2,
  },
  value: {
    fontSize: tokens.fontSizeHero700,
    fontWeight: tokens.fontWeightSemibold,
    color: tokens.colorBrandForeground1,
  },
});

function fmt(n: number, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, notation: 'compact', maximumFractionDigits: 1 }).format(n);
}

export function ARMetricsPanel() {
  const styles = useStyles();
  const { data, isLoading } = useARMetrics();
  const m = data?.data;

  return (
    <Card>
      <CardHeader
        header={<Text weight="semibold" size={500}>AR Metrics</Text>}
        action={data?.mock ? <Badge color="warning" appearance="filled">Demo Data</Badge> : null}
      />
      {isLoading || !m ? (
        <ProgressBar />
      ) : (
        <div className={styles.grid}>
          <div className={styles.metric}>
            <Text size={200}>Open AR</Text>
            <Text className={styles.value}>{fmt(m.open_ar_amount, m.currency)}</Text>
          </div>
          <div className={styles.metric}>
            <Text size={200}>DSO</Text>
            <Text className={styles.value}>{m.dso_days.toFixed(0)}d</Text>
          </div>
          <div className={styles.metric}>
            <Text size={200}>Past Due %</Text>
            <Text className={styles.value}>{(m.past_due_rate * 100).toFixed(1)}%</Text>
            <ProgressBar value={m.past_due_rate} color={m.past_due_rate > 0.2 ? 'error' : 'warning'} />
          </div>
          <div className={styles.metric}>
            <Text size={200}>Collections at Risk</Text>
            <Text className={styles.value}>{fmt(m.collections_at_risk, m.currency)}</Text>
          </div>
        </div>
      )}
    </Card>
  );
}
