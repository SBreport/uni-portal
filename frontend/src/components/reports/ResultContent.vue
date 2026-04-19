<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ReportData } from './reportSchema'

const props = defineProps<{
  title: string
  periodLabel: string
  data: ReportData
  showAnchorNav?: boolean
}>()

// ── 앵커 네비 ──
const resultSectionRefs = ref<Record<string, HTMLElement | null>>({})

function scrollToResult(key: string) {
  resultSectionRefs.value[key]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const resultNavItems = [
  { key: 'blogDistribution', label: '01 블로그배포' },
  { key: 'place', label: '02 플레이스' },
  { key: 'website', label: '03 웹사이트' },
  { key: 'blogExposure', label: '04 블로그 상위노출' },
  { key: 'related', label: '05 함께찾는' },
]

// ── KPI strip ──
interface Kpi { key: string; label: string; value: string }
const kpis = computed<Kpi[]>(() => {
  const fmt = (a: string, b: string) => (a && b ? `${a} / ${b}` : '—')
  return [
    { key: 'blog',     label: '블로그배포', value: fmt(props.data.blogDistribution.ranked,  props.data.blogDistribution.keywords) },
    { key: 'place',    label: '플레이스',   value: fmt(props.data.place.occupied,           props.data.place.total) },
    { key: 'website',  label: '웹사이트',   value: fmt(props.data.website.visible,          props.data.website.total) },
    { key: 'exposure', label: '블로그노출', value: fmt(props.data.blogExposure.visible,      props.data.blogExposure.total) },
    { key: 'related',  label: '함께찾는',   value: fmt(props.data.related.created,          props.data.related.total) },
  ]
})

// ── 생성 시각 라벨 ──
const generatedAtLabel = computed(() => {
  const now = new Date()
  const fmt = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}.${fmt(now.getMonth() + 1)}.${fmt(now.getDate())} ${fmt(now.getHours())}:${fmt(now.getMinutes())}`
})

// ── 이미지 유틸 ──
function resolveImageUrl(path: string): string {
  return `/uploads/${path}`
}

function openImagePreview(path: string) {
  window.open(resolveImageUrl(path), '_blank', 'noopener')
}
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">

    <!-- 앵커 바 (showAnchorNav 기본 true) -->
    <nav
      v-if="showAnchorNav !== false"
      class="shrink-0 border-b border-slate-200 bg-white px-5 py-2 flex items-center gap-4 overflow-x-auto"
    >
      <button
        v-for="item in resultNavItems"
        :key="item.key"
        @click="scrollToResult(item.key)"
        class="text-[11px] text-slate-500 hover:text-slate-900 whitespace-nowrap shrink-0"
      >{{ item.label }}</button>
    </nav>

    <!-- 문서 스크롤 영역 -->
    <div class="flex-1 overflow-y-auto bg-slate-50 py-5 px-5">
      <article class="mx-auto max-w-3xl bg-white border border-slate-200 rounded-lg">

        <!-- 헤더 블록 -->
        <header class="px-6 pt-6 pb-4 border-b border-slate-100">
          <h1 class="text-xl font-bold text-slate-800 mb-1">{{ title || '제목 없음' }}</h1>
          <p class="text-xs text-slate-500 tabular-nums">{{ periodLabel }}</p>
          <p v-if="data.basic.notice" class="text-[11px] text-slate-400 mt-1.5">{{ data.basic.notice }}</p>
        </header>

        <!-- KPI strip -->
        <div class="grid grid-cols-5 gap-px bg-slate-100 border-b border-slate-100">
          <div v-for="kpi in kpis" :key="kpi.key" class="bg-white px-3 py-2.5 text-center">
            <div class="text-[10px] text-slate-500 mb-1">{{ kpi.label }}</div>
            <div class="text-lg font-bold text-slate-800 tabular-nums">{{ kpi.value }}</div>
          </div>
        </div>

        <!-- 섹션 5개 -->
        <div class="divide-y divide-slate-100">

          <!-- §1 블로그배포 -->
          <section
            :ref="(el) => { resultSectionRefs['blogDistribution'] = el as HTMLElement }"
            class="px-6 py-5"
          >
            <div class="flex items-baseline gap-3 mb-4">
              <span class="text-xs font-bold text-slate-400 tabular-nums">01</span>
              <h3 class="text-sm font-bold text-slate-800">최적블로그 배포</h3>
            </div>
            <div class="grid grid-cols-3 gap-3 mb-3">
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">누적 발행 글</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.blogDistribution.posts || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">금일 상위노출 지점</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.blogDistribution.ranked || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">타겟 키워드</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.blogDistribution.keywords || '—' }}</div>
              </div>
            </div>
            <p v-if="data.blogDistribution.summary" class="text-xs text-slate-700 leading-relaxed mb-3">{{ data.blogDistribution.summary }}</p>
            <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
              <template v-if="data.blogDistribution.response">
                <dt class="text-slate-400 shrink-0">대응 중</dt>
                <dd class="text-slate-700">{{ data.blogDistribution.response }}</dd>
              </template>
              <template v-if="data.blogDistribution.link1 || data.blogDistribution.link2">
                <dt class="text-slate-400 shrink-0">원본 링크</dt>
                <dd class="text-slate-700">
                  <a v-if="data.blogDistribution.link1" :href="data.blogDistribution.link1" target="_blank" rel="noopener" class="text-blue-600 hover:underline mr-2">링크1</a>
                  <a v-if="data.blogDistribution.link2" :href="data.blogDistribution.link2" target="_blank" rel="noopener" class="text-blue-600 hover:underline">링크2</a>
                </dd>
              </template>
            </dl>
            <div v-if="data.blogDistribution.images.length > 0" class="mt-3 grid grid-cols-4 gap-2">
              <img
                v-for="img in data.blogDistribution.images"
                :key="img"
                :src="resolveImageUrl(img)"
                class="w-full h-24 object-cover rounded border border-slate-100 cursor-pointer"
                @click="openImagePreview(img)"
              />
            </div>
          </section>

          <!-- §2 플레이스 -->
          <section
            :ref="(el) => { resultSectionRefs['place'] = el as HTMLElement }"
            class="px-6 py-5"
          >
            <div class="flex items-baseline gap-3 mb-4">
              <span class="text-xs font-bold text-slate-400 tabular-nums">02</span>
              <h3 class="text-sm font-bold text-slate-800">플레이스</h3>
            </div>
            <div class="grid grid-cols-4 gap-3 mb-3">
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">총 지점</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.place.total || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">점유</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.place.occupied || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">이탈</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.place.dropped || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">휴식</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.place.paused || '—' }}</div>
              </div>
            </div>
            <p v-if="data.place.summary" class="text-xs text-slate-700 leading-relaxed mb-3">{{ data.place.summary }}</p>
            <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
              <template v-if="data.place.droppedList">
                <dt class="text-slate-400 shrink-0">이탈 지점</dt>
                <dd class="text-slate-700 whitespace-pre-wrap">{{ data.place.droppedList }}</dd>
              </template>
              <template v-if="data.place.newList">
                <dt class="text-slate-400 shrink-0">신규 지점</dt>
                <dd class="text-slate-700 whitespace-pre-wrap">{{ data.place.newList }}</dd>
              </template>
              <template v-if="data.place.pausedList">
                <dt class="text-slate-400 shrink-0">휴식 지점</dt>
                <dd class="text-slate-700 whitespace-pre-wrap">{{ data.place.pausedList }}</dd>
              </template>
              <template v-if="data.place.comment">
                <dt class="text-slate-400 shrink-0">작업 코멘트</dt>
                <dd class="text-slate-700 whitespace-pre-wrap">{{ data.place.comment }}</dd>
              </template>
              <template v-if="data.place.response">
                <dt class="text-slate-400 shrink-0">대응 중</dt>
                <dd class="text-slate-700">{{ data.place.response }}</dd>
              </template>
              <template v-if="data.place.link">
                <dt class="text-slate-400 shrink-0">원본 링크</dt>
                <dd class="text-slate-700">
                  <a :href="data.place.link" target="_blank" rel="noopener" class="text-blue-600 hover:underline">링크</a>
                </dd>
              </template>
            </dl>
            <div v-if="data.place.images.length > 0" class="mt-3 grid grid-cols-4 gap-2">
              <img
                v-for="img in data.place.images"
                :key="img"
                :src="resolveImageUrl(img)"
                class="w-full h-24 object-cover rounded border border-slate-100 cursor-pointer"
                @click="openImagePreview(img)"
              />
            </div>
          </section>

          <!-- §3 웹사이트 -->
          <section
            :ref="(el) => { resultSectionRefs['website'] = el as HTMLElement }"
            class="px-6 py-5"
          >
            <div class="flex items-baseline gap-3 mb-4">
              <span class="text-xs font-bold text-slate-400 tabular-nums">03</span>
              <h3 class="text-sm font-bold text-slate-800">웹사이트</h3>
            </div>
            <div class="grid grid-cols-4 gap-3 mb-3">
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">총 키워드</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.website.total || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">노출 지점</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.website.visible || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">이탈 지점</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.website.dropped || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">미점유 지점</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.website.missing || '—' }}</div>
              </div>
            </div>
            <p v-if="data.website.summary" class="text-xs text-slate-700 leading-relaxed mb-3">{{ data.website.summary }}</p>
            <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
              <template v-if="data.website.visibleList">
                <dt class="text-slate-400 shrink-0">현재 노출 지점</dt>
                <dd class="text-slate-700 whitespace-pre-wrap">{{ data.website.visibleList }}</dd>
              </template>
              <template v-if="data.website.response">
                <dt class="text-slate-400 shrink-0">대응 중</dt>
                <dd class="text-slate-700">{{ data.website.response }}</dd>
              </template>
              <template v-if="data.website.link">
                <dt class="text-slate-400 shrink-0">원본 링크</dt>
                <dd class="text-slate-700">
                  <a :href="data.website.link" target="_blank" rel="noopener" class="text-blue-600 hover:underline">링크</a>
                </dd>
              </template>
            </dl>
            <div v-if="data.website.images.length > 0" class="mt-3 grid grid-cols-4 gap-2">
              <img
                v-for="img in data.website.images"
                :key="img"
                :src="resolveImageUrl(img)"
                class="w-full h-24 object-cover rounded border border-slate-100 cursor-pointer"
                @click="openImagePreview(img)"
              />
            </div>
          </section>

          <!-- §4 블로그 상위노출 -->
          <section
            :ref="(el) => { resultSectionRefs['blogExposure'] = el as HTMLElement }"
            class="px-6 py-5"
          >
            <div class="flex items-baseline gap-3 mb-4">
              <span class="text-xs font-bold text-slate-400 tabular-nums">04</span>
              <h3 class="text-sm font-bold text-slate-800">블로그 상위노출</h3>
            </div>
            <div class="grid grid-cols-3 gap-3 mb-3">
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">총 키워드</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.blogExposure.total || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">노출</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.blogExposure.visible || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">이탈</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.blogExposure.dropped || '—' }}</div>
              </div>
            </div>
            <p v-if="data.blogExposure.summary" class="text-xs text-slate-700 leading-relaxed mb-3">{{ data.blogExposure.summary }}</p>
            <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
              <template v-if="data.blogExposure.response">
                <dt class="text-slate-400 shrink-0">대응 중</dt>
                <dd class="text-slate-700">{{ data.blogExposure.response }}</dd>
              </template>
              <template v-if="data.blogExposure.link">
                <dt class="text-slate-400 shrink-0">원본 링크</dt>
                <dd class="text-slate-700">
                  <a :href="data.blogExposure.link" target="_blank" rel="noopener" class="text-blue-600 hover:underline">링크</a>
                </dd>
              </template>
            </dl>
            <div v-if="data.blogExposure.images.length > 0" class="mt-3 grid grid-cols-4 gap-2">
              <img
                v-for="img in data.blogExposure.images"
                :key="img"
                :src="resolveImageUrl(img)"
                class="w-full h-24 object-cover rounded border border-slate-100 cursor-pointer"
                @click="openImagePreview(img)"
              />
            </div>
          </section>

          <!-- §5 함께찾는 -->
          <section
            :ref="(el) => { resultSectionRefs['related'] = el as HTMLElement }"
            class="px-6 py-5"
          >
            <div class="flex items-baseline gap-3 mb-4">
              <span class="text-xs font-bold text-slate-400 tabular-nums">05</span>
              <h3 class="text-sm font-bold text-slate-800">함께 많이 찾는</h3>
            </div>
            <div class="grid grid-cols-4 gap-3 mb-3">
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">총 키워드</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.related.total || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">생성</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.related.created || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">이탈</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.related.dropped || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 mb-0.5">신규</div>
                <div class="text-lg font-bold text-slate-800 tabular-nums">{{ data.related.newCount || '—' }}</div>
              </div>
            </div>
            <p v-if="data.related.summary" class="text-xs text-slate-700 leading-relaxed mb-3">{{ data.related.summary }}</p>
            <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
              <template v-if="data.related.keywords">
                <dt class="text-slate-400 shrink-0">생성 키워드</dt>
                <dd class="text-slate-700 whitespace-pre-wrap">{{ data.related.keywords }}</dd>
              </template>
              <template v-if="data.related.response">
                <dt class="text-slate-400 shrink-0">대응 중</dt>
                <dd class="text-slate-700">{{ data.related.response }}</dd>
              </template>
              <template v-if="data.related.link">
                <dt class="text-slate-400 shrink-0">원본 링크</dt>
                <dd class="text-slate-700">
                  <a :href="data.related.link" target="_blank" rel="noopener" class="text-blue-600 hover:underline">링크</a>
                </dd>
              </template>
            </dl>
            <div v-if="data.related.images.length > 0" class="mt-3 grid grid-cols-4 gap-2">
              <img
                v-for="img in data.related.images"
                :key="img"
                :src="resolveImageUrl(img)"
                class="w-full h-24 object-cover rounded border border-slate-100 cursor-pointer"
                @click="openImagePreview(img)"
              />
            </div>
          </section>

        </div>

        <!-- Footer -->
        <footer class="px-6 py-3 border-t border-slate-100 text-[10px] text-slate-400 tabular-nums">
          Generated · {{ generatedAtLabel }}
        </footer>

      </article>
    </div>
  </div>
</template>
