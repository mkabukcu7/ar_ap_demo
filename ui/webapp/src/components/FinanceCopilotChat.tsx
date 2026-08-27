import { useState, useRef, useEffect } from 'react';
import {
  Card,
  CardHeader,
  Text,
  Badge,
  Button,
  Input,
  makeStyles,
  tokens,
  Spinner,
  Accordion,
  AccordionItem,
  AccordionHeader,
  AccordionPanel,
} from '@fluentui/react-components';
import { api } from '../api/client';
import type { ChatResponse, ChatCitation, AgentTraceStep } from '../api/types';

const DEMO_PROMPTS = [
  'Show invoices awaiting approval over $10,000',
  'Why is invoice INV-1047 blocked?',
  'Approve all invoices under $2,000 with no exceptions',
  'What cash remains unapplied?',
  'Show the largest payment matching exceptions',
  'What approvals are required for invoices over $25,000?',
  'What SOX control governs invoice approvals?',
];

interface Message {
  role: 'user' | 'assistant';
  text: string;
  citations?: ChatCitation[];
  agent_trace?: AgentTraceStep[];
}

const useStyles = makeStyles({
  root: {
    display: 'flex',
    flexDirection: 'column',
    height: '520px',
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalS,
    padding: tokens.spacingVerticalS,
  },
  bubble: {
    maxWidth: '75%',
    padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`,
    borderRadius: tokens.borderRadiusLarge,
    wordBreak: 'break-word',
  },
  userBubble: {
    alignSelf: 'flex-end',
    background: tokens.colorBrandBackground,
    color: tokens.colorNeutralForegroundOnBrand,
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    background: tokens.colorNeutralBackground2,
  },
  prompts: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: tokens.spacingHorizontalXS,
    padding: `${tokens.spacingVerticalXS} ${tokens.spacingVerticalS}`,
    borderTop: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  inputRow: {
    display: 'flex',
    gap: tokens.spacingHorizontalS,
    padding: tokens.spacingVerticalS,
    borderTop: `1px solid ${tokens.colorNeutralStroke2}`,
  },
});

export function FinanceCopilotChat() {
  const styles = useStyles();
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', text: 'Hello! I\'m your Finance Copilot. Ask me anything about your invoices, approvals, AR, or financial controls.' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function send(text: string) {
    if (!text.trim() || loading) return;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setLoading(true);
    try {
      const res: ChatResponse = await api.chat(text, sessionId);
      setSessionId(res.session_id);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: res.reply, citations: res.citations, agent_trace: res.agent_trace },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: '⚠️ Could not reach the backend. (Demo mode — responses are mocked in a real deployment.)' },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader header={<Text weight="semibold" size={500}>Finance Copilot Chat</Text>} />
      <div className={styles.root}>
        <div className={styles.messages}>
          {messages.map((msg, i) => (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <div className={`${styles.bubble} ${msg.role === 'user' ? styles.userBubble : styles.assistantBubble}`}>
                <Text size={200}>{msg.text}</Text>
              </div>
              {msg.citations && msg.citations.length > 0 && (
                <Accordion collapsible style={{ maxWidth: '75%', alignSelf: 'flex-start' }}>
                  <AccordionItem value="cit">
                    <AccordionHeader size="small">
                      <Text size={100}>{msg.citations.length} citation{msg.citations.length !== 1 ? 's' : ''}</Text>
                    </AccordionHeader>
                    <AccordionPanel>
                      {msg.citations.map((c, ci) => (
                        <div key={ci} style={{ marginBottom: 8 }}>
                          <Text size={100} weight="semibold">{c.title}</Text>
                          <Text size={100} block style={{ color: tokens.colorNeutralForeground3 }}>{c.source}</Text>
                          <Text size={100} block>{c.snippet}</Text>
                        </div>
                      ))}
                    </AccordionPanel>
                  </AccordionItem>
                </Accordion>
              )}
              {msg.agent_trace && msg.agent_trace.length > 0 && (
                <Accordion collapsible style={{ maxWidth: '75%', alignSelf: 'flex-start' }}>
                  <AccordionItem value="trace">
                    <AccordionHeader size="small">
                      <Text size={100}>Agent trace ({msg.agent_trace.length} step{msg.agent_trace.length !== 1 ? 's' : ''})</Text>
                    </AccordionHeader>
                    <AccordionPanel>
                      {msg.agent_trace.map((t, ti) => (
                        <div key={ti} style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
                          <Badge appearance="tint" color="brand" size="small">{t.agent}</Badge>
                          <Badge appearance="outline" size="small">{t.tool}</Badge>
                          <Text size={100}>{t.summary}</Text>
                        </div>
                      ))}
                    </AccordionPanel>
                  </AccordionItem>
                </Accordion>
              )}
            </div>
          ))}
          {loading && (
            <div style={{ alignSelf: 'flex-start' }}>
              <Spinner size="tiny" label="Thinking…" />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className={styles.prompts}>
          {DEMO_PROMPTS.map((p) => (
            <Button key={p} size="small" appearance="outline" onClick={() => send(p)}>
              {p}
            </Button>
          ))}
        </div>

        <div className={styles.inputRow}>
          <Input
            style={{ flex: 1 }}
            placeholder="Ask a finance question…"
            value={input}
            onChange={(_, d) => setInput(d.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') void send(input); }}
            disabled={loading}
          />
          <Button appearance="primary" onClick={() => void send(input)} disabled={loading || !input.trim()}>
            Send
          </Button>
        </div>
      </div>
    </Card>
  );
}
