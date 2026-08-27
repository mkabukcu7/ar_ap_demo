import { useState } from 'react';
import {
  Card,
  CardHeader,
  Text,
  Button,
  Badge,
  Checkbox,
  Input,
  ProgressBar,
  makeStyles,
  tokens,
  Dialog,
  DialogTrigger,
  DialogSurface,
  DialogBody,
  DialogTitle,
  DialogActions,
  DialogContent,
  Label,
  Spinner,
  DataGrid,
  DataGridHeader,
  DataGridHeaderCell,
  DataGridBody,
  DataGridRow,
  DataGridCell,
  createTableColumn,
  type TableColumnDefinition,
} from '@fluentui/react-components';
import { useInvoices, useApproveInvoice, useBulkApprove } from '../api/hooks';
import type { Invoice } from '../api/types';

const useStyles = makeStyles({
  toolbar: {
    display: 'flex',
    gap: tokens.spacingHorizontalM,
    alignItems: 'flex-end',
    marginBottom: tokens.spacingVerticalS,
    flexWrap: 'wrap',
  },
  severityHigh: { color: tokens.colorPaletteRedForeground1 },
  severityMedium: { color: tokens.colorPaletteYellowForeground1 },
});

function SeverityBadge({ s }: { s: 'low' | 'medium' | 'high' }) {
  const color = s === 'high' ? 'danger' : s === 'medium' ? 'warning' : 'informative';
  return <Badge color={color} appearance="filled" size="small">{s}</Badge>;
}

export function ApprovalQueue() {
  const styles = useStyles();
  const { data, isLoading, refetch } = useInvoices({ status: 'pending_approval' });
  const approveMutation = useApproveInvoice();
  const bulkMutation = useBulkApprove();

  const [bulkMaxAmount, setBulkMaxAmount] = useState('2000');
  const [bulkNoExceptions, setBulkNoExceptions] = useState(true);
  const [bulkOpen, setBulkOpen] = useState(false);

  const invoices: Invoice[] = (data?.data.items ?? []).filter(
    (inv) => inv.status === 'pending_approval',
  );

  const columns: TableColumnDefinition<Invoice>[] = [
    createTableColumn<Invoice>({
      columnId: 'invoice_id',
      renderHeaderCell: () => 'Invoice',
      renderCell: (inv) => <Text size={200}>{inv.invoice_id}</Text>,
    }),
    createTableColumn<Invoice>({
      columnId: 'vendor_name',
      renderHeaderCell: () => 'Vendor',
      renderCell: (inv) => inv.vendor_name,
    }),
    createTableColumn<Invoice>({
      columnId: 'total_amount',
      renderHeaderCell: () => 'Amount',
      renderCell: (inv) => `$${inv.total_amount.toLocaleString()}`,
    }),
    createTableColumn<Invoice>({
      columnId: 'po_number',
      renderHeaderCell: () => 'PO',
      renderCell: (inv) => inv.po_number ?? '—',
    }),
    createTableColumn<Invoice>({
      columnId: 'approver',
      renderHeaderCell: () => 'Approver',
      renderCell: (inv) => inv.approver,
    }),
    createTableColumn<Invoice>({
      columnId: 'exceptions',
      renderHeaderCell: () => 'Exceptions',
      renderCell: (inv) =>
        inv.exceptions.length > 0 ? (
          <SeverityBadge s={inv.exceptions[0].severity} />
        ) : (
          <Badge color="success" appearance="filled" size="small">None</Badge>
        ),
    }),
    createTableColumn<Invoice>({
      columnId: 'actions',
      renderHeaderCell: () => '',
      renderCell: (inv) => (
        <Button
          appearance="primary"
          size="small"
          disabled={approveMutation.isPending}
          onClick={() => approveMutation.mutate({ invoice_id: inv.invoice_id })}
        >
          Approve
        </Button>
      ),
    }),
  ];

  return (
    <Card>
      <CardHeader
        header={<Text weight="semibold" size={500}>Approval Queue</Text>}
        action={
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {data?.mock && <Badge color="warning" appearance="filled">Demo Data</Badge>}
            <Badge appearance="tint" color="warning">{invoices.length} pending</Badge>
          </div>
        }
      />

      <div className={styles.toolbar}>
        <Dialog open={bulkOpen} onOpenChange={(_, d) => setBulkOpen(d.open)}>
          <DialogTrigger disableButtonEnhancement>
            <Button appearance="outline" size="small">Bulk Approve…</Button>
          </DialogTrigger>
          <DialogSurface>
            <DialogBody>
              <DialogTitle>Bulk Approve Invoices</DialogTitle>
              <DialogContent>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <Label>Max Amount ($)</Label>
                  <Input
                    type="number"
                    value={bulkMaxAmount}
                    onChange={(_, d) => setBulkMaxAmount(d.value)}
                  />
                  <Checkbox
                    label="Require no exceptions"
                    checked={bulkNoExceptions}
                    onChange={(_, d) => setBulkNoExceptions(!!d.checked)}
                  />
                </div>
              </DialogContent>
              <DialogActions>
                <DialogTrigger disableButtonEnhancement>
                  <Button appearance="secondary">Cancel</Button>
                </DialogTrigger>
                <Button
                  appearance="primary"
                  disabled={bulkMutation.isPending}
                  onClick={() => {
                    bulkMutation.mutate(
                      {
                        max_amount: Number(bulkMaxAmount),
                        require_no_exceptions: bulkNoExceptions,
                      },
                      {
                        onSuccess: () => {
                          setBulkOpen(false);
                          void refetch();
                        },
                      },
                    );
                  }}
                >
                  {bulkMutation.isPending ? <Spinner size="tiny" /> : 'Approve'}
                </Button>
              </DialogActions>
            </DialogBody>
          </DialogSurface>
        </Dialog>
      </div>

      {isLoading ? (
        <ProgressBar />
      ) : (
        <DataGrid items={invoices} columns={columns} getRowId={(inv) => inv.invoice_id}>
          <DataGridHeader>
            <DataGridRow>
              {({ renderHeaderCell }) => (
                <DataGridHeaderCell>{renderHeaderCell()}</DataGridHeaderCell>
              )}
            </DataGridRow>
          </DataGridHeader>
          <DataGridBody<Invoice>>
            {({ item, rowId }) => (
              <DataGridRow<Invoice> key={rowId}>
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
