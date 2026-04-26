import { useState } from "react";
import {
  Card, Space, Button, Typography, List, Tag, Empty, message,
  Popconfirm, Modal, Form, Input, Divider,
} from "antd";
import {
  DeleteOutlined, PlusOutlined, ReloadOutlined, EditOutlined,
} from "@ant-design/icons";
import RegionSelector from "../components/RegionSelector";
import CropSelector from "../components/CropSelector";
import {
  listMemories, createMemoryItem, updateMemoryItem, deleteMemoryItem,
  type MemoryItemDTO, type RegionDTO, type CropDTO,
} from "../services/api";

const { Text, Title } = Typography;

export default function MemoryPage() {
  const [regionId, setRegionId] = useState<number | null>(null);
  const [region, setRegion] = useState<RegionDTO | null>(null);
  const [cropId, setCropId] = useState<number | null>(null);
  const [crop, setCrop] = useState<CropDTO | null>(null);
  const [items, setItems] = useState<MemoryItemDTO[]>([]);
  const [loading, setLoading] = useState(false);

  const [addOpen, setAddOpen] = useState(false);
  const [editItem, setEditItem] = useState<MemoryItemDTO | null>(null);
  const [form] = Form.useForm();

  const load = async () => {
    if (!regionId || !cropId) return;
    setLoading(true);
    try {
      const { data } = await listMemories(regionId, cropId);
      setItems(data.items);
    } finally {
      setLoading(false);
    }
  };

  const handleRegionChange = (id: number | null, r: RegionDTO | null) => {
    setRegionId(id); setRegion(r); setItems([]);
    if (id && cropId) setTimeout(load, 0);
  };
  const handleCropChange = (id: number | null, c: CropDTO | null) => {
    setCropId(id); setCrop(c); setItems([]);
    if (id && regionId) setTimeout(load, 0);
  };

  const handleAdd = async (values: { key: string; value: string }) => {
    if (!regionId || !cropId) return;
    try {
      await createMemoryItem(regionId, cropId, values.key, values.value);
      message.success("已添加");
      setAddOpen(false); form.resetFields();
      load();
    } catch (err: any) {
      message.error(err.response?.data?.detail || "添加失败");
    }
  };

  const handleEdit = async (values: { value: string }) => {
    if (!editItem) return;
    try {
      await updateMemoryItem(editItem.id, values.value);
      message.success("已更新");
      setEditItem(null); form.resetFields();
      load();
    } catch (err: any) {
      message.error(err.response?.data?.detail || "更新失败");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteMemoryItem(id);
      message.success("已删除");
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch {
      message.error("删除失败");
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: "0 auto" }}>
      <Title level={4}>🧠 长期记忆管理</Title>
      <Text type="secondary">
        按「区域 + 作物」查看和管理您的长期信息（如地块面积、土壤类型、历年病虫害等）。
      </Text>

      <Card style={{ marginTop: 16 }}>
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <Text strong>选择区域</Text>
            <RegionSelector value={regionId} onChange={handleRegionChange} />
          </div>
          <div>
            <Text strong>选择作物</Text>
            <CropSelector value={cropId} onChange={handleCropChange} />
          </div>
          {region && crop && (
            <Tag color="green">
              📍 {region.full_name} · 🌱 {crop.name}
            </Tag>
          )}
        </Space>
      </Card>

      <Card
        style={{ marginTop: 16 }}
        title="记忆条目"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />} onClick={load}
              disabled={!regionId || !cropId}
            >刷新</Button>
            <Button
              type="primary" icon={<PlusOutlined />}
              onClick={() => setAddOpen(true)}
              disabled={!regionId || !cropId}
            >新增</Button>
          </Space>
        }
        loading={loading}
      >
        {!regionId || !cropId ? (
          <Empty description="请先选择区域和作物" />
        ) : items.length === 0 ? (
          <Empty description="暂无记忆条目" />
        ) : (
          <List
            dataSource={items}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button
                    type="text" size="small" icon={<EditOutlined />}
                    onClick={() => {
                      setEditItem(item);
                      form.setFieldsValue({ value: item.value });
                    }}
                  >编辑</Button>,
                  <Popconfirm title="删除此条记忆？" onConfirm={() => handleDelete(item.id)}>
                    <Button type="text" size="small" icon={<DeleteOutlined />} danger>删除</Button>
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text code>{item.key}</Text>
                      {item.source === "ai_extracted"
                        ? <Tag color="blue">AI提取</Tag>
                        : <Tag color="green">用户确认</Tag>}
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        置信度 {Math.round(item.confidence * 100)}%
                      </Text>
                    </Space>
                  }
                  description={
                    <div>
                      <div style={{ fontSize: 14, color: "#262626" }}>{item.value}</div>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        创建于 {new Date(item.created_at).toLocaleString("zh-CN")}
                      </Text>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>

      <Modal
        title="新增记忆条目"
        open={addOpen}
        onOk={() => form.submit()}
        onCancel={() => { setAddOpen(false); form.resetFields(); }}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item
            label="键 (key)" name="key"
            rules={[{ required: true, max: 64 }]}
            extra="例如：field_size / soil_type / irrigation"
          >
            <Input placeholder="field_size" />
          </Form.Item>
          <Form.Item
            label="值 (value)" name="value"
            rules={[{ required: true, min: 1, max: 500 }]}
          >
            <Input.TextArea rows={3} placeholder="例如：约30亩，黏土质" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`编辑：${editItem?.key}`}
        open={editItem !== null}
        onOk={() => form.submit()}
        onCancel={() => { setEditItem(null); form.resetFields(); }}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleEdit}>
          <Form.Item
            label="值" name="value"
            rules={[{ required: true, min: 1, max: 500 }]}
          >
            <Input.TextArea rows={3} />
          </Form.Item>
          <Divider />
          <Text type="secondary" style={{ fontSize: 12 }}>
            如需修改 key，请删除后重新添加。
          </Text>
        </Form>
      </Modal>
    </div>
  );
}
