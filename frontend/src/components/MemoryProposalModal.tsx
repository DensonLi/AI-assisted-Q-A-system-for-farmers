import { useEffect, useState } from "react";
import {
  Modal, List, Button, Tag, Typography, Space, Empty, Progress, message,
} from "antd";
import {
  CheckOutlined, CloseOutlined, BulbOutlined,
} from "@ant-design/icons";
import {
  listMemoryProposals, acceptMemoryProposal, rejectMemoryProposal,
  type MemoryProposalDTO,
} from "../services/api";

const { Text, Paragraph } = Typography;

interface Props {
  open: boolean;
  conversationId: number;
  onClose: () => void;
  /** 处理完成后通知父组件刷新（例如记忆摘要侧栏） */
  onProcessed?: () => void;
}

const ACTION_LABEL: Record<string, { text: string; color: string }> = {
  add: { text: "新增", color: "green" },
  update: { text: "更新", color: "blue" },
  delete: { text: "删除", color: "red" },
};

export default function MemoryProposalModal({
  open, conversationId, onClose, onProcessed,
}: Props) {
  const [proposals, setProposals] = useState<MemoryProposalDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState<Record<number, "accept" | "reject" | undefined>>({});

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await listMemoryProposals(conversationId);
      setProposals(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, conversationId]);

  const handleAccept = async (p: MemoryProposalDTO) => {
    setProcessing((s) => ({ ...s, [p.id]: "accept" }));
    try {
      await acceptMemoryProposal(p.id);
      setProposals((prev) => prev.filter((x) => x.id !== p.id));
      onProcessed?.();
      message.success("已保存到长期记忆");
    } catch {
      message.error("操作失败");
    } finally {
      setProcessing((s) => ({ ...s, [p.id]: undefined }));
    }
  };

  const handleReject = async (p: MemoryProposalDTO) => {
    setProcessing((s) => ({ ...s, [p.id]: "reject" }));
    try {
      await rejectMemoryProposal(p.id);
      setProposals((prev) => prev.filter((x) => x.id !== p.id));
      onProcessed?.();
    } catch {
      message.error("操作失败");
    } finally {
      setProcessing((s) => ({ ...s, [p.id]: undefined }));
    }
  };

  return (
    <Modal
      title={
        <Space>
          <BulbOutlined style={{ color: "#faad14" }} />
          <span>AI 识别到的新信息，请确认是否保存</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={
        <Button onClick={onClose}>关闭（稍后处理）</Button>
      }
      width={640}
      destroyOnClose
    >
      {loading ? (
        <div style={{ textAlign: "center", padding: 32 }}>加载中...</div>
      ) : proposals.length === 0 ? (
        <Empty description="暂无待确认的记忆更新" />
      ) : (
        <>
          <Paragraph type="secondary" style={{ fontSize: 13 }}>
            系统从您本轮对话中提取出以下可能与您田块相关的长期信息。确认后将在未来问答中被自动考虑。
          </Paragraph>
          <List
            dataSource={proposals}
            renderItem={(p) => {
              const action = ACTION_LABEL[p.action] ?? { text: p.action, color: "default" };
              const confPct = Math.round(p.confidence * 100);
              return (
                <List.Item
                  style={{
                    padding: 12, marginBottom: 8,
                    border: "1px solid #f0f0f0", borderRadius: 6,
                    background: "#fafafa",
                  }}
                  actions={[
                    <Button
                      size="small" type="primary" icon={<CheckOutlined />}
                      loading={processing[p.id] === "accept"}
                      disabled={processing[p.id] === "reject"}
                      onClick={() => handleAccept(p)}
                    >确认</Button>,
                    <Button
                      size="small" danger icon={<CloseOutlined />}
                      loading={processing[p.id] === "reject"}
                      disabled={processing[p.id] === "accept"}
                      onClick={() => handleReject(p)}
                    >拒绝</Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <Tag color={action.color}>{action.text}</Tag>
                        <Text code>{p.key}</Text>
                      </Space>
                    }
                    description={
                      <div>
                        {p.existing_value && p.action === "update" && (
                          <div style={{ fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>
                            原值: <Text delete>{p.existing_value}</Text>
                          </div>
                        )}
                        <div style={{ fontSize: 14, color: "#262626" }}>
                          {p.action === "delete" ? "删除此条" : <Text strong>{p.proposed_value}</Text>}
                        </div>
                        {p.reason && (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            依据: {p.reason}
                          </Text>
                        )}
                        <div style={{ marginTop: 6 }}>
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            置信度 {confPct}%
                          </Text>
                          <Progress
                            percent={confPct}
                            showInfo={false}
                            size="small"
                            strokeColor={confPct >= 80 ? "#52c41a" : confPct >= 60 ? "#faad14" : "#ff4d4f"}
                          />
                        </div>
                      </div>
                    }
                  />
                </List.Item>
              );
            }}
          />
        </>
      )}
    </Modal>
  );
}
