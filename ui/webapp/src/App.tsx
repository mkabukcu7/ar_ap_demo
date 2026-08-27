import { useState } from 'react';
import {
  FluentProvider,
  webLightTheme,
  webDarkTheme,
  Tab,
  TabList,
  Text,
  Button,
  makeStyles,
  tokens,
  Badge,
} from '@fluentui/react-components';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InvoicePipeline } from './components/InvoicePipeline';
import { ApprovalQueue } from './components/ApprovalQueue';
import { APMetricsPanel } from './components/APMetricsPanel';
import { ARMetricsPanel } from './components/ARMetricsPanel';
import { CashApplicationStatus } from './components/CashApplicationStatus';
import { ExceptionQueue } from './components/ExceptionQueue';
import { AgentActivityFeed } from './components/AgentActivityFeed';
import { FinanceCopilotChat } from './components/FinanceCopilotChat';

const queryClient = new QueryClient();

type TabValue =
  | 'ap'
  | 'ar'
  | 'pipeline'
  | 'approvals'
  | 'cash'
  | 'exceptions'
  | 'activity'
  | 'chat';

const useStyles = makeStyles({
  shell: {
    minHeight: '100vh',
    background: tokens.colorNeutralBackground1,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalXL}`,
    background: tokens.colorBrandBackground,
    color: tokens.colorNeutralForegroundOnBrand,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalM,
  },
  nav: {
    background: tokens.colorNeutralBackground2,
    borderBottom: `1px solid ${tokens.colorNeutralStroke1}`,
    paddingLeft: tokens.spacingHorizontalL,
  },
  content: {
    padding: `${tokens.spacingVerticalL} ${tokens.spacingHorizontalXL}`,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalL,
    maxWidth: '1400px',
    margin: '0 auto',
  },
  twoCol: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: tokens.spacingHorizontalL,
    '@media (max-width: 900px)': {
      gridTemplateColumns: '1fr',
    },
  },
});

function Dashboard() {
  const styles = useStyles();
  const [tab, setTab] = useState<TabValue>('ap');
  const [dark, setDark] = useState(false);

  return (
    <FluentProvider theme={dark ? webDarkTheme : webLightTheme}>
      <div className={styles.shell}>
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <Text size={600} weight="bold" style={{ color: '#fff' }}>
              Finance Operations Command Center
            </Text>
            <Badge appearance="filled" color="success" size="small">Azure AI Foundry</Badge>
          </div>
          <Button
            appearance="subtle"
            onClick={() => setDark((d) => !d)}
            style={{ color: '#fff' }}
          >
            {dark ? '☀ Light' : '🌙 Dark'}
          </Button>
        </header>

        <nav className={styles.nav}>
          <TabList
            selectedValue={tab}
            onTabSelect={(_, d) => setTab(d.value as TabValue)}
          >
            <Tab value="ap">AP Metrics</Tab>
            <Tab value="ar">AR Metrics</Tab>
            <Tab value="pipeline">Invoice Pipeline</Tab>
            <Tab value="approvals">Approval Queue</Tab>
            <Tab value="cash">Cash Application</Tab>
            <Tab value="exceptions">Exceptions</Tab>
            <Tab value="activity">Agent Activity</Tab>
            <Tab value="chat">Copilot Chat</Tab>
          </TabList>
        </nav>

        <main className={styles.content}>
          {tab === 'ap' && (
            <>
              <APMetricsPanel />
              <InvoicePipeline />
            </>
          )}
          {tab === 'ar' && (
            <>
              <ARMetricsPanel />
              <CashApplicationStatus />
            </>
          )}
          {tab === 'pipeline' && <InvoicePipeline />}
          {tab === 'approvals' && <ApprovalQueue />}
          {tab === 'cash' && <CashApplicationStatus />}
          {tab === 'exceptions' && <ExceptionQueue />}
          {tab === 'activity' && (
            <div className={styles.twoCol}>
              <AgentActivityFeed />
              <APMetricsPanel />
            </div>
          )}
          {tab === 'chat' && (
            <div className={styles.twoCol}>
              <FinanceCopilotChat />
              <AgentActivityFeed />
            </div>
          )}
        </main>
      </div>
    </FluentProvider>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  );
}

export default App;
