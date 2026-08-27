import {
  Card,
  CardHeader,
  Text,
  Badge,
  ProgressBar,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { useAgentActivity } from '../api/hooks';
import type { AgentActivity } from '../api/types';

const useStyles = makeStyles({
  feed: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalXS,
    maxHeight: '360px',
    overflowY: 'auto',
    padding: tokens.spacingVerticalXS,
  },
  item: {
    display: 'flex',
    gap: tokens.spacingHorizontalM,
    alignItems: 'flex-start',
    padding: tokens.spacingVerticalXS,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  meta: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    gap: '2px',
  },
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    marginTop: '6px',
    flexShrink: 0,
  },
  running: { background: tokens.colorPaletteYellowBackground3 },
  succeeded: { background: tokens.colorPaletteGreenBackground3 },
  failed: { background: tokens.colorPaletteRedBackground3 },
});

function StatusDot({ status }: { status: AgentActivity['status'] }) {
  const styles = useStyles();
  const cls = `${styles.dot} ${status === 'running' ? styles.running : status === 'succeeded' ? styles.succeeded : styles.failed}`;
  return <span className={cls} />;
}

function fmtTime(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return ts;
  }
}

export function AgentActivityFeed() {
  const styles = useStyles();
  const { data, isLoading } = useAgentActivity();
  const items = data?.data.items ?? [];

  return (
    <Card>
      <CardHeader
        header={<Text weight="semibold" size={500}>Agent Activity Feed</Text>}
        action={data?.mock ? <Badge color="warning" appearance="filled">Demo Data</Badge> : null}
      />
      {isLoading ? (
        <ProgressBar />
      ) : (
        <div className={styles.feed}>
          {items.map((item, i) => (
            <div key={i} className={styles.item}>
              <StatusDot status={item.status} />
              <div className={styles.meta}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <Text size={200} weight="semibold">{item.agent}</Text>
                  <Badge
                    appearance="tint"
                    color={item.status === 'succeeded' ? 'success' : item.status === 'failed' ? 'danger' : 'warning'}
                    size="small"
                  >
                    {item.status}
                  </Badge>
                </div>
                <Text size={200}>{item.action} — {item.detail}</Text>
                <Text size={100} style={{ color: tokens.colorNeutralForeground3 }}>
                  {fmtTime(item.timestamp)}
                </Text>
              </div>
            </div>
          ))}
          {items.length === 0 && <Text size={200}>No agent activity yet.</Text>}
        </div>
      )}
    </Card>
  );
}
