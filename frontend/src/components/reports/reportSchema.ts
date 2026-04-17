export interface ReportData {
  basic: {
    notice: string
  }
  blogDistribution: {
    posts: string
    ranked: string
    keywords: string
    summary: string
    response: string
    link1: string
    link2: string
    images: string[]
  }
  place: {
    total: string
    occupied: string
    dropped: string
    paused: string
    summary: string
    response: string
    droppedList: string
    newList: string
    pausedList: string
    comment: string
    link: string
    images: string[]
  }
  website: {
    total: string
    visible: string
    dropped: string
    missing: string
    summary: string
    response: string
    visibleList: string
    link: string
    images: string[]
  }
  blogExposure: {
    total: string
    visible: string
    dropped: string
    summary: string
    response: string
    link: string
    images: string[]
  }
  related: {
    total: string
    created: string
    dropped: string
    newCount: string
    summary: string
    response: string
    keywords: string
    link: string
    images: string[]
  }
}

export function createEmptyReportData(): ReportData {
  return {
    basic: { notice: '' },
    blogDistribution: { posts: '', ranked: '', keywords: '', summary: '', response: '', link1: '', link2: '', images: [] },
    place: { total: '', occupied: '', dropped: '', paused: '', summary: '', response: '', droppedList: '', newList: '', pausedList: '', comment: '', link: '', images: [] },
    website: { total: '', visible: '', dropped: '', missing: '', summary: '', response: '', visibleList: '', link: '', images: [] },
    blogExposure: { total: '', visible: '', dropped: '', summary: '', response: '', link: '', images: [] },
    related: { total: '', created: '', dropped: '', newCount: '', summary: '', response: '', keywords: '', link: '', images: [] },
  }
}

export function mergeReportData(serverData: Record<string, any>): ReportData {
  const empty = createEmptyReportData()
  return {
    basic: { ...empty.basic, ...(serverData.basic ?? {}) },
    blogDistribution: {
      ...empty.blogDistribution,
      ...(serverData.blogDistribution ?? {}),
      images: serverData.blogDistribution?.images ?? [],
    },
    place: {
      ...empty.place,
      ...(serverData.place ?? {}),
      images: serverData.place?.images ?? [],
    },
    website: {
      ...empty.website,
      ...(serverData.website ?? {}),
      images: serverData.website?.images ?? [],
    },
    blogExposure: {
      ...empty.blogExposure,
      ...(serverData.blogExposure ?? {}),
      images: serverData.blogExposure?.images ?? [],
    },
    related: {
      ...empty.related,
      ...(serverData.related ?? {}),
      images: serverData.related?.images ?? [],
    },
  }
}
