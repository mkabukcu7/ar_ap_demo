import {
  Card,
  CardHeader,
  Text,
  Badge,
  ProgressBar,
  makeStyles,
  tokens,
  DataGrid,
  DataGridHeader,
  DataGridHeaderCell,
  DataGridBody,
  DataGridRow,
  DataGridCell,
  createTableColumn,
  type TableColumnDefinition,
} from '@fluentui/react-components';
import { useExceptions } from '../api/hooks';
import type { ExceptionItem } from '../api/types';

const useStyles = makeStyles({
  domainBadge: { marginLeft: tokens.spacingHorizontalXS },
});

function SeverityBadge({ s }: { s: 'low' | 'medium' | 'high' }) {
  const color = s === 'high' ? 'danger' : s === 'medium' ? 'warning' : 'informative';
  return <Badge color={color} appearance="filled" size="small">{s}</Badge>;
}

export function ExceptionQueue() {
  const styles = useStyles();
  const { data, isLoading } = useExceptions();
  const items: ExceptionItem[] = data?.data.items ?? [];

  const columns: TableColumnDefinition<ExceptionItem>[] = [
    createTableColumn<ExceptionItem>({
      columnId: 'document',
      renderHeaderCell: () => 'Document',
      renderCell: (ex) => (
        <Text size={200}>
          {ex.invoice_id ?? ex.document_id ?? '—'}
          <Badge
            className={styles.domainBadge}
            appearance="tint"
            color={ex.domain === 'ap' ? 'brand' : 'informative'}
            size="small"
          >
            {ex.domain.toUpperCase()}
          </Badge>
        </Text>
      ),
    }),
    createTableColumn<ExceptionItem>({
      columnId: 'code',
      renderHeaderCell: () => 'Code',
      renderCell: (ex) => <Text size={200}>{ex.code}</Text>,
    }),
    createTableColumn<ExceptionItem>({
      columnId: 'severity',
      renderHeaderCell: () => 'Severity',
      renderCell: (ex) => <SeverityBadge s={ex.severity} />,
    }),
    createTableColumn<ExceptionItem>({
      columnId: 'message',
      renderHeaderCell: () => 'Description',
      renderCell: (ex) => <Text size={200}>{ex.message}</Text>,
    }),
    createTableColumn<ExceptionItem>({
      columnId: 'amount',
      renderHeaderCell: () => 'Amount',
      renderCell: (ex) =>
        ex.amount ? `$${ex.amount.toLocaleString()}` : '—',
    }),
  ];

  return (
    <Card>
      <CardHeader
        header={<Text weight="semibold" size={500}>Exception Queue</Text>}
        action={
          <div style={{ display: 'flex', gap: 8 }}>
            {data?.mock && <Badge color="warning" appearance="filled">Demo Data</Badge>}
            <Badge appearance="tint" color="danger">{items.length} exceptions</Badge>
          </div>
        }
      />
      {isLoading ? (
        <ProgressBar />
      ) : (
        <DataGrid items={items} columns={columns} getRowId={(item: ExceptionItem) => `${item.domain}-${item.code}-${item.invoice_id ?? item.document_id ?? ''}`}>
          <DataGridHeader>
            <DataGridRow>
              {({ renderHeaderCell }) => (
                <DataGridHeaderCell>{renderHeaderCell()}</DataGridHeaderCell>
              )}
            </DataGridRow>
          </DataGridHeader>
          <DataGridBody<ExceptionItem>>
            {({ item, rowId }) => (
              <DataGridRow<ExceptionItem> key={rowId}>
                {({ renderCell }) => (
                  <DataGridCell>{renderCell(item)}</DataGridCell>
                )}
              </DataGridRow>
            )}
          </DataGridBody>
        </DataGrid>
      )}
    </Card>
  );
}
