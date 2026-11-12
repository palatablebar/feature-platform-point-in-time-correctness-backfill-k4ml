<template>
  <section class="card">
    <div class="card-title">
      <h2>同键来源合并</h2>
      <span class="op-index">
        来源 {{ summary.input_rows ?? 0 }} 行 → 入选 {{ summary.included_records ?? 0 }} · 冲突
        {{ summary.conflict_records ?? 0 }} · 排除 {{ summary.excluded_records ?? 0 }}
      </span>
    </div>

    <p v-if="!summary.input_rows" class="muted small">
      尚无合并台账：先运行样本任务。同一账户、同一观察时刻在多个标签集里各有一条标签时，
      会在这里给出入选 / 冲突 / 排除三份名单。
    </p>

    <template v-else>
      <p class="small muted">
        按 <span class="mono">(entity_key, label_time)</span> 合成一份可训练记录：标签一致保留全部来源；
        标签冲突整条键退出训练。名单只按样本键与来源编号排序，与标签集勾选顺序无关，同一批数据重跑不新增样本。
      </p>

      <details class="merge-block" :open="conflicts.length > 0">
        <summary>
          冲突记录 · <strong class="mono" :style="{ color: conflicts.length ? 'var(--annot)' : 'inherit' }">{{ conflicts.length }}</strong>
          <span class="muted small">（同键标签不一致，整条退出训练）</span>
        </summary>
        <p v-if="conflicts.length === 0" class="muted small">没有同键标签冲突。</p>
        <template v-else>
          <table>
            <thead>
              <tr><th>实体</th><th>观察时刻</th><th>冲突标签</th><th>来源投票</th><th>处置</th></tr>
            </thead>
            <tbody>
              <tr v-for="record in shownConflicts" :key="`${record.entity_key}-${record.label_time}`">
                <td>{{ record.entity_key }}</td>
                <td>{{ fmtShortTime(record.label_time) }}</td>
                <td style="color: var(--annot)">{{ record.labels.join(' / ') }}</td>
                <td>
                  <span v-for="source in record.sources" :key="source.label_row_id" class="mono" style="font-size: 0.72rem">
                    {{ source.label_set_code || `LS#${source.label_set_id}` }}→{{ source.label }}
                  </span>
                </td>
                <td style="color: var(--annot)">退出训练</td>
              </tr>
            </tbody>
          </table>
          <p v-if="conflicts.length > limit" class="small muted">共 {{ conflicts.length }} 条，仅展示前 {{ limit }} 条。</p>
        </template>
      </details>

      <details class="merge-block">
        <summary>
          入选记录 · <strong class="mono">{{ included.length }}</strong>
          <span class="muted small">（同键标签一致，合成一条可训练记录）</span>
        </summary>
        <p v-if="included.length === 0" class="muted small">没有可训练记录。</p>
        <template v-else>
          <table>
            <thead>
              <tr><th>实体</th><th>观察时刻</th><th>y</th><th>来源数</th><th>全部来源</th></tr>
            </thead>
            <tbody>
              <tr v-for="record in shownIncluded" :key="`${record.entity_key}-${record.label_time}`">
                <td>{{ record.entity_key }}</td>
                <td>{{ fmtShortTime(record.label_time) }}</td>
                <td>{{ record.label }}</td>
                <td class="mono">{{ record.source_count }}</td>
                <td>
                  <span v-for="source in record.sources" :key="source.label_row_id" class="mono" style="font-size: 0.72rem">
                    {{ source.label_set_code || `LS#${source.label_set_id}` }}→{{ source.label }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="included.length > limit" class="small muted">共 {{ included.length }} 条，仅展示前 {{ limit }} 条。</p>
        </template>
      </details>

      <details class="merge-block">
        <summary>
          排除记录 · <strong class="mono">{{ excluded.length }}</strong>
          <span class="muted small">（被折叠的重复来源 + 冲突键的全部来源，逐行留痕）</span>
        </summary>
        <p v-if="excluded.length === 0" class="muted small">没有排除记录：每个来源行都各自成键。</p>
        <template v-else>
          <table>
            <thead>
              <tr><th>实体</th><th>观察时刻</th><th>来源</th><th>标签</th><th>排除原因</th></tr>
            </thead>
            <tbody>
              <tr v-for="record in shownExcluded" :key="record.label_row_id">
                <td>{{ record.entity_key }}</td>
                <td>{{ fmtShortTime(record.label_time) }}</td>
                <td class="mono" style="font-size: 0.72rem">{{ record.label_set_code || `LS#${record.label_set_id}` }}</td>
                <td>{{ record.label }}</td>
                <td :style="{ color: record.reason === 'label_conflict' ? 'var(--annot)' : 'inherit' }">
                  {{ EXCLUSION_REASON[record.reason] ?? record.reason }}
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="excluded.length > limit" class="small muted">共 {{ excluded.length }} 条，仅展示前 {{ limit }} 条。</p>
        </template>
      </details>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { EXCLUSION_REASON } from '../../constants/enums'
import type { ConflictRecord, ExcludedRecord, IncludedRecord, MergeSummary } from '../../types/sample'
import { fmtShortTime } from '../../utils/format'

const props = withDefaults(
  defineProps<{
    summary: MergeSummary | null
    included: IncludedRecord[]
    conflicts: ConflictRecord[]
    excluded: ExcludedRecord[]
    limit?: number
  }>(),
  { limit: 50 },
)

const summary = computed(() => props.summary ?? ({} as MergeSummary))
const included = computed(() => props.included ?? [])
const conflicts = computed(() => props.conflicts ?? [])
const excluded = computed(() => props.excluded ?? [])

const shownIncluded = computed(() => included.value.slice(0, props.limit))
const shownConflicts = computed(() => conflicts.value.slice(0, props.limit))
const shownExcluded = computed(() => excluded.value.slice(0, props.limit))
</script>

<style scoped>
.merge-block {
  margin-top: var(--space-3, 12px);
}
.merge-block > summary {
  cursor: pointer;
  font-weight: 600;
  padding: 6px 0;
}
.merge-block table {
  margin-top: 6px;
}
.merge-block td span + span::before {
  content: ' · ';
  color: var(--ink-soft, #888);
}
</style>
