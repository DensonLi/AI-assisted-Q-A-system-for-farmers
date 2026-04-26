import { useEffect, useState } from "react";
import {
  Card, List, Typography, Empty, Spin, Tag, Button, Space, Popconfirm, message,
} from "antd";
import { DeleteOutlined, ReloadOutlined } from "@ant-design/icons";
import {
  listMemories, deleteMemoryItem, type MemoryItemDTO,
} from "../services/api";

const { Text } = Typography;

interface Props {
  regionId: number | null;
  cropId: number | null;
  regionName?: string;
  cropName?: string;
  phenologyStage?: string | null;
  /** 父组件触发刷新的 token（每次 +1 即刷新） */
  reloadToken?: number;
}

export default function MemoryPanel({
  regionId, cropId, regionName, cropName, phenologyStage, reloadToken,
}: Props) {
  const [items, setItems] = useState<MemoryItemDTO[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    if (!regionId || !cropId) { setItems([]); return; }
    setLoading(true);
    try {
      const { data } = await listMemories(regionId, cropId);
      setItems(data.items);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [regionId, cropId, reloadToken]);

  const handleDelete = async (id: number) => {
    try {
      await deleteMemoryItem(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
      message.success("已删除");
    } catch {
      message.error("删除失败");
    }
  };

  return (
    <Card
      size="small"
      title={
        <Space>
          <span style={{ fontSize: 13 }}>📋 长期记忆</span>
          <Button
            type="text" size="small" icon={<ReloadOutlined />}
            onClick={load} disabled={!regionId || !cropId}
          />
        </Space>
      }
      style={{ margin: 12 }}
      bodyStyle={{ padding: 8, maxHeight: "calc(100vh - 260px)", overflow: "auto" }}
    >
      {regionName && cropName && (
        <div style={{ padding: "4px 8px", fontSize: 12, color: "#595959" }}>
          📍 {regionName}<br/>
          🌱 {cropName}
          {phenologyStage && (
            <><br/><Tag color="orange" style={{ marginTop: 4 }}>{phenologyStage}</Tag></>
          )}
        </div>
      )}
      {loading ? (
        <div style={{ textAlign: "center", padding: 24 }}><Spin size="small" /></div>
      ) : !regionId || !cropId ? (
        <Empty
          description={<Text type="secondary" style={{ fontSize: 12 }}>选择对话后显示</Text>}
          imageStyle={{ height: 40 }}
        />
      ) : items.length === 0 ? (
        <Empty
          description={<Text type="secondary" style={{ fontSize: 12 }}>暂无记忆条目</Text>}
          imageStyle={{ height: 40 }}
        />
      ) : (
        <List
          dataSource={items}
          size="small"
          renderItem={(item) => (
            <List.Item
              style={{ padding: "6px 8px", fontSize: 12 }}
              actions={[
                <Popconfirm
                  title="删除此条记忆？"
                  onConfirm={() => handleDelete(item.id)}
                >
                  <Button type="text" size="small" icon={<DeleteOutlined />} danger />
                </Popconfirm>,
              ]}
            >
              <div style={{ width: "100%" }}>
                <div>
                  <Text code style={{ fontSize: 11 }}>{item.key}</Text>
                  {item.source === "ai_extracted" && (
                    <Tag color="blue" style={{ marginLeft: 4, fontSize: 10 }}>AI</Tag>
                  )}
                  {item.source === "user_confirmed" && (
                    <Tag color="green" style={{ marginLeft: 4, fontSize: 10 }}>已确认</Tag>
                  )}
                </div>
                <div style={{ color: "#262626", marginTop: 2 }}>{item.value}</div>
              </div>
            </List.Item>
          )}
        />
      )}
    </Card>
  );
}
