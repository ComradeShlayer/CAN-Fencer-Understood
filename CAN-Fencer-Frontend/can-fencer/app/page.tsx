import supabase from '../lib/supabase'

export default async function Home() {
  const { data, error } = await supabase
    .from('results')
    .select(`
      placement,
      fencers(name),
      events(name)
    `)
    .limit(20)

  if (error) {
    return <div>Error: {error.message}</div>
  }

  return (
    <div style={{ padding: "20px" }}>
      <h1>Recent Results</h1>

      {data?.map((r, i) => (
        <div key={i}>
          {r.placement} - {r.fencers?.name} ({r.events?.name})
        </div>
      ))}
    </div>
  )
}