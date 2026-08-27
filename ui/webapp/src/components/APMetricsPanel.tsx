import {
  Card,
  CardHeader,
  Text,
  Badge,
  ProgressBar,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useAPMetrics } from '../api/hooks';

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

export function APMetricsPanel() {
  const styles = useStyles();
  const { data, isLoading } = useAPMetrics();
  const m = data?.data;

  return (
    <Card>
      <CardHeader
        header={<Text weight="semibold" size={500}>AP Metrics</Text>}
        action={data?.mock ? <Badge color="warning" appearance="filled">Demo Data</Badge> : null}
      />
      {isLoading || !m ? (
        <ProgressBar />
      ) : (
        <div className={styles.grid}>
          <div className={styles.metric}>
            <Text size={200}>Total Invoices</Text>
            <Text className={styles.value}>{m.total_invoices.toLocaleString()}</Text>
          </div>
          <div className={styles.metric}>
            <Text size={200}>Awaiting Approval</Text>
            <Text className={styles.value}>{m.awaiting_approval}</Text>
          </div>
          <div className={styles.metric}>
            <Text size={200}>Touchless Rate</Text>
            <Text className={styles.value}>{(m.touchless_rate * 100).toFixed(1)}%</Text>
            <ProgressBar value={m.touchless_rate} color="success" />
          </div>
          <div className={styles.metric}>
            <Text size={200}>Avg Cycle Time</Text>
            <Text className={styles.value}>{m.avg_cycle_time_days.toFixed(1)}d</Text>
          </div>
          <div className={styles.metric}>
            <Text size={200}>Exception Rate</Text>
            <Text className={styles.value}>{(m.exception_rate * 100).toFixed(1)}%</Text>
            <ProgressBar value={m.exception_rate} color={m.exception_rate > 0.1 ? 'error' : 'warning'} />
          </div>
          <div className={styles.metric}>
            <Text size={200}>Total Spend</Text>
            <Text className={styles.value}>{fmt(m.total_spend, m.currency)}</Text>
          </div>
        </div>
      )}
    </Card>
  );
}
