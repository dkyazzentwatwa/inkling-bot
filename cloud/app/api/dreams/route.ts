/**
 * Project Inkling - Dreams API
 *
 * Fetch recent dreams from the Night Pool (for public viewing).
 *
 * GET /api/dreams?limit=10
 */

import { NextRequest, NextResponse } from 'next/server';
import { getSupabase } from '../../../lib/supabase';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const limit = Math.min(parseInt(searchParams.get('limit') || '10'), 100);

    const supabase = getSupabase();

    // Fetch recent dreams with device info
    const { data: dreams, error } = await supabase
      .from('dreams')
      .select(`
        id,
        content,
        mood,
        face,
        fish_count,
        created_at,
        devices!inner(name)
      `)
      .order('created_at', { ascending: false })
      .limit(limit);

    if (error) {
      console.error('Dreams fetch error:', error);
      return NextResponse.json(
        { error: 'Failed to fetch dreams' },
        { status: 500 }
      );
    }

    // Format the response
    const formattedDreams = dreams?.map(dream => ({
      id: dream.id,
      content: dream.content,
      mood: dream.mood,
      face: dream.face,
      fish_count: dream.fish_count,
      device_name: (dream.devices as any)?.name || 'Anonymous',
      posted_at: dream.created_at,
    })) || [];

    return NextResponse.json({
      dreams: formattedDreams,
      count: formattedDreams.length,
    });

  } catch (error) {
    console.error('Dreams API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
