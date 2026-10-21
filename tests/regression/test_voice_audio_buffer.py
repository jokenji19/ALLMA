"""Run the actual Java producer/consumer bridge under real concurrent threads."""
from pathlib import Path
import os
import subprocess


def test_audio_buffer_order_bounded_waits_cancel_and_error_preservation(tmp_path):
    root=Path(__file__).resolve().parents[2]
    source=root/'libs/android_src/org/allma/voice/VoiceAudioBuffer.java'
    test=tmp_path/'VoiceBufferCheck.java'
    test.write_text('''
import org.allma.voice.VoiceAudioBuffer;
import java.util.concurrent.atomic.AtomicBoolean;
public class VoiceBufferCheck {
 public static void main(String[] args) throws Exception {
  AtomicBoolean active=new AtomicBoolean(true);
  VoiceAudioBuffer copy=new VoiceAudioBuffer();
  float[] source={1,2};copy.put(source,active::get);source[0]=99;copy.finish(null);
  if(copy.take(active::get)[0]!=1 || copy.take(active::get)!=null)throw new AssertionError("ownership");
  VoiceAudioBuffer queue=new VoiceAudioBuffer();
  Thread producer=new Thread(()->{try{for(int i=0;i<100;i++)if(!queue.put(new float[]{i},active::get))throw new AssertionError();queue.finish(null);}catch(Exception e){throw new RuntimeException(e);}});
  producer.start();int count=0;float[] item;
  while((item=queue.take(active::get))!=null){if(item[0]!=count++)throw new AssertionError("lost or reordered samples");}
  producer.join(1000);if(count!=100 || producer.isAlive())throw new AssertionError("completion");
  VoiceAudioBuffer bounded=new VoiceAudioBuffer();
  for(int i=0;i<4;i++)bounded.put(new float[]{i},active::get);
  Thread blocked=new Thread(()->{try{bounded.put(new float[]{5},active::get);}catch(Exception e){throw new RuntimeException(e);}});
  blocked.start();Thread.sleep(100);if(!blocked.isAlive())throw new AssertionError("queue not bounded");
  active.set(false);blocked.join(500);if(blocked.isAlive())throw new AssertionError("cancel producer");
  AtomicBoolean listening=new AtomicBoolean(true);VoiceAudioBuffer empty=new VoiceAudioBuffer();
  Thread consumer=new Thread(()->{try{empty.take(listening::get);}catch(Exception e){throw new RuntimeException(e);}});
  consumer.start();Thread.sleep(100);listening.set(false);consumer.join(500);
  if(consumer.isAlive())throw new AssertionError("cancel consumer");
  RuntimeException failure=new RuntimeException("synthetic failure");
  empty.finish(failure);empty.finish(null);if(empty.failure()!=failure)throw new AssertionError("lost failure");
  System.out.println("PASS: order, ownership, bounded queue, producer cancellation, consumer cancellation, failure preservation");
 }
}
''')
    jdk=Path(os.environ.get('JAVA_HOME','/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home'))/'bin'
    subprocess.run([str(jdk/'javac'),'-d',str(tmp_path),str(source),str(test)],check=True,capture_output=True,timeout=30)
    check=subprocess.run([str(jdk/'java'),'-cp',str(tmp_path),'VoiceBufferCheck'],check=True,capture_output=True,text=True,timeout=10)
    assert check.stdout.startswith('PASS:')
