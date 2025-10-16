export interface PipelineRun {
  id: number;
  task_type: string;
  status: string;
  start_time: string;
  end_time: string | null;
  total_products: number;
  processed_products: number;
  failed_products: number;
}
