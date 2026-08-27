import {
  Card,
  CardHeader,
  Text,
  ProgressBar,
  Badge,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { usePipeline } from '../api/hooks';

const STAGE_ORDER = ['Received', 'Extracted', 'Validated', 'Matched', 'Approval', 'Posted'];

const useStyles = makeStyles({
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: tokens.spacingHorizontalM,
    marginTop: tokens.spacingVerticalM,
  },
  stageCard: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalXS,
    padding: tokens.spacingHorizontalM,
  },
  count: {
    fontSize: tokens.fontSizeHero800,
    fontWeight: tokens.fontWeightSemibold,
    color: tokens.colorBrandForeground1,
  },
});

export function InvoicePipeline() {
  const styles = useStyles();
  const { data, isLoading } = usePipeline();
  const stages = data?.data.stages ?? [];
  const total = stages.reduce((s, x) => s + x.count, 0) || 1;

  const sorted = STAGE_ORDER.map((name) => ({
    stage: name,
    count: stages.find((s) => s.stage.toLowerCase() === name.toLowerCase())?.count ?? 0,
  }));

  return (
    <Card>
      <CardHeader
        header={<Text weight="semibold" size={500}>Invoice Pipeline</Text>}
        action={data?.mock ? <Badge color="warning" appearance="filled">Demo Data</Badge> : null}
      />
      {isLoading ? (
        <ProgressBar />
      ) : (
        <div className={styles.grid}>
          {sorted.map(({ stage, count }) => (
            <div key={stage} className={styles.stageCard}>
              <Text size={200} weight="semibold">{stage}</Text>
              <Text className={styles.count}>{count}</Text>
              <ProgressBar
                value={count / total}
                color={stage === 'Approval' ? 'warning' : 'brand'}
                thickness="medium"
              />
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
