import {
  Card,
  CardHeader,
  Text,
  Badge,
  ProgressBar,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useUnapplied, useRemittances } from '../api/hooks';

const useStyles = makeStyles({
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: tokens.spacingHorizontalM,
    padding: tokens.spacingVerticalS,
  },
  bucket: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalXS,
    padding: tokens.spacingHorizontalM,
    borderRadius: tokens.borderRadiusMedium,
    background: tokens.colorNeutralBackground2,
    alignItems: 'center',
    textAlign: 'center',
  },
  value: {
    fontSize: tokens.fontSizeHero700,
    fontWeight: tokens.fontWeightSemibold,
  },
  applied: { color: tokens.colorPaletteGreenForeground1 },
  partial: { color: tokens.colorPaletteYellowForeground1 },
  unapplied: { color: tokens.colorPaletteRedForeground1 },
});

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 }).format(n);
}

export function CashApplicationStatus() {
  const styles = useStyles();
  const { data: remData, isLoading } = useRemittances();
  const { data: unapplData } = useUnapplied();
  const items = remData?.data.items ?? [];

  const applied = items.filter((r) => r.status === 'applied').length;
  const partial = items.filter((r) => r.status === 'partially_applied').length;
  const unapplied = items.filter((r) => r.status === 'unapplied').length;
  const total = items.length || 1;

  const mock = remData?.mock || unapplData?.mock;

  return (
    <Card>
      <CardHeader
        header={<Text weight="semibold" size={500}>Cash Application Status</Text>}
        action={mock ? <Badge color="warning" appearance="filled">Demo Data</Badge> : null}
      />
      {isLoading ? (
        <ProgressBar />
      ) : (
        <>
          <div className={styles.grid}>
            <div className={styles.bucket}>
              <Text size={200} weight="semibold">Applied</Text>
              <Text className={`${styles.value} ${styles.applied}`}>{applied}</Text>
              <ProgressBar value={applied / total} color="success" />
            </div>
            <div className={styles.bucket}>
              <Text size={200} weight="semibold">Partially Applied</Text>
              <Text className={`${styles.value} ${styles.partial}`}>{partial}</Text>
              <ProgressBar value={partial / total} color="warning" />
            </div>
            <div className={styles.bucket}>
              <Text size={200} weight="semibold">Unapplied</Text>
              <Text className={`${styles.value} ${styles.unapplied}`}>{unapplied}</Text>
              <ProgressBar value={unapplied / total} color="error" />
            </div>
          </div>
          {unapplData?.data.total_unapplied != null && (
            <Text size={200} style={{ padding: '8px 12px' }}>
              Total unapplied cash: <strong>{fmt(unapplData.data.total_unapplied)}</strong>
            </Text>
          )}
        </>
      )}
    </Card>
  );
}
